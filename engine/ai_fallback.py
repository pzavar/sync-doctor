import json

import anthropic

from engine.matcher import Match

MODEL = "claude-haiku-5-5"  # the only place the model name lives; fast and cheap
THRESHOLD = 0.85  # raised from 0.7: a wrong card costs more than a "Not sure"

SYSTEM = """You classify NetSuite sync errors from Ramp into a fixed catalog.
Choose exactly one catalog id from the list provided, or "unknown" if none fits.
Give your confidence from 0 to 1 and a one-sentence reason.
Never write fix steps."""


def _schema(ids: list[str]) -> dict:
    """JSON schema the API enforces. The enum means the model cannot return an id we don't have."""
    return {
        "type": "object",
        "properties": {
            "catalog_id": {"type": "string", "enum": ids + ["unknown"]},
            "confidence": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["catalog_id", "confidence", "reason"],
        "additionalProperties": False,
    }


def make_classifier(catalog, api_key, threshold=THRESHOLD):
    """Return a classify(raw_error) function bound to this catalog and key."""
    client = anthropic.Anthropic(api_key=api_key)
    ids = list(catalog["id"])
    valid_ids = set(ids)
    schema = _schema(ids)
    options = "\n".join(f"{r.id}: {r.category}. {r.cause}" for r in catalog.itertuples())

    def classify(raw_error: str) -> Match:
        try:
            resp = client.messages.create(
                model=MODEL,
                # Haiku 5.5 thinks before answering, and thinking counts toward max_tokens.
                # 200 could be used up before any JSON is written, so leave room.
                max_tokens=1024,
                system=SYSTEM,
                output_config={"effort": "low",
                               "format": {"type": "json_schema", "schema": schema}},
                messages=[{"role": "user",
                           "content": f"Catalog:\n{options}\n\nError:\n{raw_error}"}],
            )
            if resp.stop_reason != "end_turn":  # e.g. max_tokens or refusal: no usable answer
                return Match(None, "ai", 0.0, note=f"AI gave no answer ({resp.stop_reason})")
            data = json.loads(next(b.text for b in resp.content if b.type == "text"))
            cid = data["catalog_id"]
            conf = float(data["confidence"])
            reason = str(data["reason"])
        # Network trouble, a bad key, or an unparseable reply: fail safe, not loud.
        # Narrower than `except Exception`, so a real bug in this code still surfaces.
        except (anthropic.APIError, ValueError, KeyError, StopIteration) as e:
            return Match(None, "ai", 0.0, note=f"AI unavailable ({type(e).__name__})")

        # Second guard: the schema already limits ids, but never trust one guard alone.
        if cid not in valid_ids or conf < threshold:
            return Match(None, "ai", conf, note=reason)
        return Match(cid, "ai", conf, note=reason)

    return classify
