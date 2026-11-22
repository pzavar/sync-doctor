"""Check the AI fallback on 12 hand-made errors the rules don't cover.

Run from the repo root:
    python -m scripts.validate_ai            live: 12 API calls, needs .streamlit/secrets.toml
    python -m scripts.validate_ai --offline  only checks that the rules miss every input
Prints markdown tables. Results from the last run are saved in docs/ai_validation.md.
"""
import sys
import tomllib

from engine.catalog import load_catalog
from engine.matcher import match_rule
from engine.ai_fallback import make_classifier, THRESHOLD

# Expected answer for each input. "unknown" means the right move is to decline.
NOVEL = [  # verbatim from data/novel_errors.txt, deliberately not in the catalog
    ("Discount item was not found", "unknown"),
    ("AccountingSyncAmountInfo.currency_ref is required to sync transaction in original currency (Transaction ID: {transaction_id} )", "unknown"),
    ("The currency on the transaction, {txn_currency} is different from {entity_currency}, the currency of the entity, {entity_name} on this transaction.", "unknown"),
]
OTHER_SYSTEMS = [  # verbatim from Ramp's QuickBooks articles; chosen because they LOOK like catalog rows
    # https://support.ramp.com/quickbooks-online-sync-error-account-period-closed  (resembles PER-001)
    ("Account Period Closed", "unknown"),
    # https://support.ramp.com/quickbooks-desktop-sync-error-the-value-selected-for-vendor-was-not-found-please-select-an-active-value  (resembles VEN-001)
    ("The value selected for Vendor was not found. Please select an active value.", "unknown"),
]
REWORDED = [  # SYNTHETIC rewordings of catalog errors, as if NetSuite changed its phrasing. Test inputs only.
    ("Unable to determine the NetSuite subsidiary for this bill. Make sure this entity is linked to a NetSuite subsidiary in your Ramp Accounting Settings.", "SUB-001"),
    ("Accounting period closed in the accounting provider. Reopen the period or move the accounting date into an open period.", "PER-001"),
    ("Missing required value: Primary Subsidiary", "SUB-003"),
    ("Bill payment could not be synced: the bill has already been paid in NetSuite.", "PAY-002"),
    ("Access denied: the integration role's Pay Bills permission level is too low for this page.", "PERM-002"),
    ("NetSuite rejected the Vendor Bill: an invoice attachment is required before this bill can be saved.", "REQ-003"),
    ("Vendor could not be created in NetSuite because another vendor record already has this name.", "VEN-002"),
]

cat = load_catalog()
cases = ([("novel", e, x) for e, x in NOVEL] + [("other sys", e, x) for e, x in OTHER_SYSTEMS]
         + [("reworded", e, x) for e, x in REWORDED])

caught = [(e[:50], match_rule(e, cat).catalog_id) for _, e, _ in cases if match_rule(e, cat)]
print("Inputs the rules already catch (must be none):", caught or "none")
if "--offline" in sys.argv:
    sys.exit(0)

with open(".streamlit/secrets.toml", "rb") as f:
    key = tomllib.load(f)["ANTHROPIC_API_KEY"]  # loaded, never printed
raw = make_classifier(cat, key, threshold=0.0)  # threshold 0 so we see the model's raw pick

tally = {"correct pick": 0, "correct decline": 0, "wrong pick": 0, "missed": 0}
print("\n| Set | Error | Expected | AI's pick | Confidence | Verdict |")
print("|---|---|---|---|---|---|")
for kind, err, expected in cases:
    m = raw(err)
    pick = m.catalog_id or "unknown"
    if pick == "unknown" or m.confidence < THRESHOLD:
        verdict = "correct decline" if expected == "unknown" else "missed"
    else:
        verdict = "correct pick" if pick == expected else "wrong pick"
    tally[verdict] += 1
    print(f"| {kind} | {err} | {expected} | {pick} | {m.confidence:.2f} | {verdict} |")

print(f"\n| Cases | Correct picks | Correct declines | Wrong picks | Missed |")
print("|---|---|---|---|---|")
print(f"| {len(cases)} | {tally['correct pick']} | {tally['correct decline']} | "
      f"{tally['wrong pick']} | {tally['missed']} |")
