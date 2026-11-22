import pytest

from engine.catalog import load_catalog

CAT = load_catalog()
RULE_ROWS = CAT[CAT["regex"].notna()]


def first_match_id(raw_error: str):
    """First catalog row whose regex matches. Mirrors the matcher's rule (Step 4)."""
    for row in RULE_ROWS.itertuples():
        if row.regex.search(raw_error):
            return row.id
    return None


@pytest.mark.parametrize("row", RULE_ROWS.to_dict("records"), ids=lambda r: r["id"])
def test_example_matches_its_own_row(row):
    matched = first_match_id(row["example_error"])
    assert matched is not None, "pattern does not match its own example"
    assert matched == row["id"], f"{matched} matched first. Check catalog order."
