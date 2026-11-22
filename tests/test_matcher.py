"""Protects the numbers the demo depends on, and two design decisions."""
import pandas as pd

from engine.catalog import load_catalog
from engine.matcher import Match, triage
from engine.grouping import root_causes
from engine.preflight import load_northwind, preflight

CAT = load_catalog()


def sample():
    # Read as text, the same way the app does.
    return pd.read_csv("data/sample_failures.csv", dtype=str).fillna("")


def test_sample_counts_add_up():
    df = triage(sample(), CAT)
    assert root_causes(df)["failures"].sum() == len(df) == 60


def test_top_group_is_uk_subsidiary():
    top = root_causes(triage(sample(), CAT)).iloc[0]
    assert (top["catalog_id"], top["group_value"], top["failures"]) == ("SUB-001", "Northwind UK", 25)


def test_preflight_finds_the_six_planted_problems():
    issues = preflight(**load_northwind(), catalog=CAT)
    assert sorted(issues["object_id"]) == [
        "RMP-1004", "RMP-1005", "RMP-1006", "RMP-1007", "RMP-1008", "RMP-1009"]


def test_gusto_is_one_group_in_triage_and_preflight():
    """NetSuite's VEN-001 error names an internal ID, so both sides group by it."""
    def ven(groups):
        return groups[groups["catalog_id"] == "VEN-001"][["group_value", "label"]].values.tolist()

    expected = [["1482", "Gusto (1482)"]]
    assert ven(root_causes(triage(sample(), CAT))) == expected
    assert ven(root_causes(preflight(**load_northwind(), catalog=CAT))) == expected


def test_ai_suggestions_never_inflate_a_rule_group():
    """An AI match for Northwind UK gets its own group, ranked last. No API call: fake classifier."""
    extra = sample().iloc[[0]].assign(object_id="RMP-9999", ramp_entity="Northwind UK",
                                      raw_error="Wording no rule has seen")
    fake = lambda e: Match("SUB-001", "ai", 0.9, note="test")
    groups = root_causes(triage(pd.concat([sample(), extra]), CAT, classify=fake))

    assert (groups.iloc[0]["failures"], groups.iloc[0]["suggested"]) == (25, False)
    last = groups.iloc[-1]
    assert (last["catalog_id"], last["failures"], last["suggested"]) == ("SUB-001", 1, True)
    assert last["headline"].startswith("Suggested:")
