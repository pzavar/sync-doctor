from dataclasses import dataclass, field
import pandas as pd


@dataclass
class Match:
    catalog_id: str | None   # None means unrecognized
    method: str              # "rule", "ai", or "none"
    confidence: float
    values: dict = field(default_factory=dict)  # named groups, like {"field": "Location"}
    note: str = ""           # the AI's one-line reason, if any


def match_rule(raw_error: str, catalog: pd.DataFrame) -> Match | None:
    """Return the first catalog row whose regex matches, or None."""
    for row in catalog.itertuples():
        if row.regex is None:  # pre-flight-only row
            continue
        m = row.regex.search(str(raw_error))
        if m:
            return Match(row.id, "rule", 1.0, m.groupdict())
    return None


def triage(failures: pd.DataFrame, catalog: pd.DataFrame, classify=None) -> pd.DataFrame:
    """Attach a catalog match to every failure row.

    classify is an optional function for rule misses (the AI fallback).
    Passing it in keeps this file testable without an API key.
    """
    out = []
    for rec in failures.to_dict("records"):
        m = match_rule(rec["raw_error"], catalog)
        if m is None and classify is not None:
            m = classify(rec["raw_error"])
        if m is None:
            m = Match(None, "none", 0.0)
        out.append({
            **rec,
            "catalog_id": m.catalog_id,
            "method": m.method,
            "confidence": m.confidence,
            "note": m.note,
            **{f"v_{k}": v for k, v in m.values.items()},
        })
    result = pd.DataFrame(out)
    details = catalog.drop(columns=["regex"])
    return result.merge(details, left_on="catalog_id", right_on="id", how="left")
