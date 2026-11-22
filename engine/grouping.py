import pandas as pd


def group_value(row) -> str:
    """The specific thing that makes two errors the same problem."""
    key = row.get("group_key")
    if not isinstance(key, str) or not key:
        return ""
    # Check a value pulled from the error first, then the failure's own column.
    for col in (f"v_{key}", key):
        val = row.get(col)
        if isinstance(val, str) and val:
            return val
    return ""


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def label(g) -> str:
    """The group's value as a person should read it: 'Gusto (1482)', not '1482'."""
    vendors = [v for v in g["vendors"] if v]
    # Only name the vendor when every row agrees. NetSuite's error can refer to an
    # account instead, and a wrong name is worse than a bare ID.
    if g["group_key"] == "internal_id" and g["group_value"] and len(vendors) == 1:
        return f"{vendors[0]} ({g['group_value']})"
    return g["group_value"]


def headline(g) -> str:
    n = g["failures"]
    if g["catalog_id"] == "UNRECOGNIZED":
        verb = "needs" if n == 1 else "need"
        return f"{plural(n, 'error')} {verb} a human look."
    target = f"{g['label']}: " if g["label"] else ""
    if g["suggested"]:
        # AI picks are never presented as fact. Confidence can't tell right from wrong
        # (docs/ai_validation.md), so a person checks before anyone acts.
        return (f"Suggested: {target}{g['cause']} The AI matched {plural(n, 'failure')} "
                f"(${g['dollars']:,.0f}) here. Check before fixing.")
    # Pre-flight issues haven't failed yet, so fixing them prevents failures.
    verb = "prevent" if g["preflight"] else "clear"
    return (f"{target}{g['cause']} Fix this to {verb} {plural(n, 'failure')} "
            f"(${g['dollars']:,.0f}).")


def root_causes(triaged: pd.DataFrame) -> pd.DataFrame:
    df = triaged.copy()
    df["catalog_id"] = df["catalog_id"].fillna("UNRECOGNIZED")
    df["group_value"] = df.apply(group_value, axis=1)
    # CSVs are read as text. Without this, sum() would join "120.5" and "88" as strings.
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    # AI-suggested rows get their own groups, so they never inflate a rule-based count.
    df["suggested"] = (df["method"] == "ai") & (df["catalog_id"] != "UNRECOGNIZED")
    groups = (
        df.groupby(["catalog_id", "group_value", "suggested"])
          .agg(failures=("object_id", "count"),
               dollars=("amount", "sum"),
               object_ids=("object_id", list),
               vendors=("vendor", lambda s: sorted(set(s))),
               preflight=("method", lambda s: (s == "preflight").all()))
          .reset_index()
          # Rule-based groups first (suggested=False sorts before True), then count, then dollars.
          .sort_values(["suggested", "failures", "dollars"], ascending=[True, False, False])
    )
    details = df.drop_duplicates("catalog_id")[
        ["catalog_id", "category", "owner", "cause", "fix_steps", "ramp_url", "group_key"]
    ]
    groups = groups.merge(details, on="catalog_id", how="left")
    groups["label"] = groups.apply(label, axis=1)
    groups["headline"] = groups.apply(headline, axis=1)
    return groups
