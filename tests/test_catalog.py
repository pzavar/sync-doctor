"""Protects the catalog, the file that gets edited most."""
import pytest

from engine.catalog import load_catalog
from engine.matcher import match_rule

CAT = load_catalog()
RULE_ROWS = CAT[CAT["regex"].notna()]


@pytest.mark.parametrize("row", RULE_ROWS.to_dict("records"), ids=lambda r: r["id"])
def test_example_matches_its_own_row(row):
    m = match_rule(row["example_error"], CAT)
    assert m is not None, "pattern does not match its own example"
    assert m.catalog_id == row["id"], f"{m.catalog_id} matched first. Check catalog order."


# Rows that cover more than one error message. The catalog holds one example per row,
# so the extra messages are pinned here.
EXTRA_CASES = [
    # Merged from the old SUB-004 row. Same broken setting: entity not linked to a subsidiary.
    # Source: https://support.ramp.com/netsuite-sync-error-bill-has-no-entity-or-subsidiary
    ("Bill has no Entity or Subsidiary", "SUB-001"),
]


@pytest.mark.parametrize("raw_error, expected", EXTRA_CASES)
def test_extra_messages_match_their_row(raw_error, expected):
    m = match_rule(raw_error, CAT)
    assert m is not None and m.catalog_id == expected
