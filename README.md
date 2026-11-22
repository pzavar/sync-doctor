# Sync Doctor

Triage Ramp to NetSuite sync errors in seconds.

[Live app](TODO-after-deploy) · [4 minute demo](TODO-after-recording)

## The problem
<!-- DRAFT: rewrite in your own voice -->
When a Ramp transaction fails to sync, the customer sees NetSuite's raw error message. The person who sees it, usually someone in AP, often isn't the person who can fix it: that might be a NetSuite admin, a Ramp admin, or the controller. During month-end close, dozens of failures can pile up, and most of them come from a handful of broken settings.

## What it does
- **Triage:** any error becomes a cause, an owner, fix steps, and Ramp's help link.
- **Root-cause grouping:** a batch of failures becomes a ranked list of fixes, ordered by failures cleared, then dollars.
- **Pre-flight:** checks next month's spend against the NetSuite setup and predicts failures before a sync runs.

The demo customer is Northwind Labs, a fictional company on NetSuite OneWorld with US, UK, and Canada subsidiaries. Each tab has a "Load Northwind sample data" button.

## How it works
- **Catalog** ([data/catalog.csv](data/catalog.csv)): 24 known errors across 8 categories. Each has a regex, an owner, a cause, fix steps, and a Ramp help link. Every other part reads from it.
- **Rules matcher** ([engine/matcher.py](engine/matcher.py)): tries each regex in order, and the first match wins. Values in the error, like a field name or account number, are pulled out for grouping.
- **AI fallback** ([engine/ai_fallback.py](engine/ai_fallback.py)): runs only when no rule matches. Three guards:
  1. The API's structured output limits the answer to a catalog ID or "unknown".
  2. The code re-checks the ID and drops anything under 0.85 confidence.
  3. The app shows every AI match as a labeled suggestion, never as an answer.
- **Grouping** ([engine/grouping.py](engine/grouping.py)): failures are the same problem when they match the same catalog row and the same value. For example, 25 subsidiary errors for Northwind UK are one fix. AI-suggested rows get their own groups.
- **Pre-flight** ([engine/preflight.py](engine/preflight.py)): checks spend against entity mappings, accounts, vendors, open periods, and required fields. Its output has the same shape as triage, so grouping and the fix cards work on both.
- **App** ([app.py](app.py)): Streamlit, with three tabs. The `engine/` folder never imports Streamlit, so it's testable on its own.

The app works without an API key; the AI is simply off. With a key, AI answers are cached, failed calls are not, and each visitor is capped at 25 AI calls per session.

## AI validation: rules give answers, the AI gives suggestions

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

## Run it locally
Requires Python 3.11 or newer.
```
git clone https://github.com/pzavar/sync-doctor.git
cd sync-doctor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Optional, to turn the AI on: create `.streamlit/secrets.toml` containing `ANTHROPIC_API_KEY = "your-key"`. This file is gitignored.

Run the tests with `python -m pytest -v`. Re-run the AI validation with `python -m scripts.validate_ai`, which makes 12 API calls.

## Disclaimer
Independent project. Not affiliated with Ramp or Oracle NetSuite. All data is synthetic. Fix steps are written in my own words and link to Ramp's official help articles.
