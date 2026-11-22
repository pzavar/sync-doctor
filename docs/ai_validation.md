# AI fallback: validation on 12 hand-made cases

The AI fallback only runs when no catalog rule matches an error. These 12 cases check what it does then.

- **Run on:** 2026-11-21, model `claude-haiku-5-5`, effort `low`, structured outputs restricted to catalog IDs plus `unknown`.
- **Floor:** a suggestion is shown only at confidence 0.85 or higher. Below that, the app shows "Not sure".
- **Reproduce:** `python -m scripts.validate_ai` from the repo root. It makes 12 API calls and needs `.streamlit/secrets.toml`.

## The cases

| Set | Count | Where the text comes from | Right answer |
|---|---|---|---|
| novel | 3 | Verbatim from Ramp help articles, deliberately left out of the catalog (`data/novel_errors.txt`) | unknown |
| other sys | 2 | Verbatim QuickBooks errors from Ramp help articles, picked because they look like catalog rows | unknown |
| reworded | 7 | **Synthetic.** Catalog errors rewritten as if NetSuite changed its wording | the original row |

None of the 12 match a catalog rule, so every one reaches the AI. The script checks this before it calls the API.

## Results

| Set | Error | Expected | AI's pick | Confidence | Verdict |
|---|---|---|---|---|---|
| novel | Discount item was not found | unknown | VEN-001 | 0.60 | correct decline |
| novel | AccountingSyncAmountInfo.currency_ref is required to sync transaction in original currency (Transaction ID: {transaction_id} ) | unknown | REQ-001 | 0.80 | correct decline |
| novel | The currency on the transaction, {txn_currency} is different from {entity_currency}, the currency of the entity, {entity_name} on this transaction. | unknown | unknown | 0.85 | correct decline |
| other sys | Account Period Closed | unknown | PER-001 | 0.95 | wrong pick |
| other sys | The value selected for Vendor was not found. Please select an active value. | unknown | VEN-001 | 0.90 | wrong pick |
| reworded | Unable to determine the NetSuite subsidiary for this bill. Make sure this entity is linked to a NetSuite subsidiary in your Ramp Accounting Settings. | SUB-001 | SUB-001 | 0.95 | correct pick |
| reworded | Accounting period closed in the accounting provider. Reopen the period or move the accounting date into an open period. | PER-001 | PER-001 | 0.90 | correct pick |
| reworded | Missing required value: Primary Subsidiary | SUB-003 | SUB-003 | 0.90 | correct pick |
| reworded | Bill payment could not be synced: the bill has already been paid in NetSuite. | PAY-002 | PAY-002 | 0.95 | correct pick |
| reworded | Access denied: the integration role's Pay Bills permission level is too low for this page. | PERM-002 | PERM-002 | 0.95 | correct pick |
| reworded | NetSuite rejected the Vendor Bill: an invoice attachment is required before this bill can be saved. | REQ-003 | REQ-003 | 0.93 | correct pick |
| reworded | Vendor could not be created in NetSuite because another vendor record already has this name. | VEN-002 | VEN-002 | 0.93 | correct pick |

A pick below 0.85 counts as a decline, because the app never shows it.

| Cases | Correct picks | Correct declines | Wrong picks | Missed |
|---|---|---|---|---|
| 12 | 7 | 3 | 2 | 0 |

## What this shows

- **Confidence does not separate right from wrong.** Wrong picks scored 0.90 and 0.95. Correct picks scored 0.90 to 0.95. No threshold blocks one without blocking the other, so the app shows AI matches as suggestions, never as answers.
- **The AI matches on meaning, not source.** It mapped two QuickBooks errors to the NetSuite rows they resemble. This doesn't affect real use, because Sync Doctor only reads Ramp-to-NetSuite logs.
- **Scores move between runs.** The currency_ref error scored 0.85, 0.80 and 0.80 across three runs, so it lands on either side of the floor. Twelve cases is a sanity check, not an accuracy rate.

## Changes made because of earlier runs

1. **Floor at 0.7, 8 cases:** 2 wrong picks. One came from two catalog rows describing the same broken setting. SUB-004 was merged into SUB-001.
2. **Prompt line "errors not from NetSuite are unknown," 12 cases:** 3 wrong picks and 1 miss. The AI can't tell an error's source from its text, and the line made it doubt real NetSuite errors. The line was removed.
3. **Floor raised to 0.85:** kept, as the minimum for showing any suggestion at all.
