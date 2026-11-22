# Sync Doctor

Triage Ramp to NetSuite sync errors in seconds.

Work in progress. Full README comes in Step 9.

## How the AI is used: rules give answers, the AI gives suggestions

Catalog rules match known errors exactly, and they always run first. The AI (Claude Haiku) only sees errors that no rule matches. It can pick one catalog row or say "unknown". It never writes fix text.

I tested it on 12 hand-made cases:
- 3 real errors deliberately left out of the catalog
- 2 QuickBooks errors that look like NetSuite ones
- 7 synthetic rewordings of catalog errors

| Cases | Correct picks | Correct declines | Wrong picks | Missed |
|---|---|---|---|---|
| 12 | 7 | 3 | 2 | 0 |

The model's confidence scores overlapped between right and wrong answers. Both wrong picks scored 0.90 or higher, the same as the correct ones. A confidence threshold can't tell them apart, so the app shows every AI match as an "AI suggestion" with its reason, and keeps AI-suggested rows out of the rule-based groups. A score of 0.85 is only the minimum for showing a suggestion at all.

Both wrong picks were the QuickBooks errors, which the AI mapped to the NetSuite rows they resemble. That shows it matches on meaning, not on source. It doesn't affect real use, because Sync Doctor only reads Ramp-to-NetSuite logs.

Full table and method: [docs/ai_validation.md](docs/ai_validation.md).

## Disclaimer
Independent project. Not affiliated with Ramp or Oracle NetSuite. All data is synthetic.
