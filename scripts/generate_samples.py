"""Generate synthetic failed syncs for the fictional Northwind Labs."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # same data every run, so the demo never changes

ENTITIES = ["Northwind US", "Northwind UK", "Northwind Canada"]
VENDORS = ["AWS", "Figma", "WeWork", "Delta", "Uline", "Gusto", "Notion", "Zoom"]
TYPES = ["card transaction", "bill", "reimbursement", "bill payment"]

# Fixed column order. DictWriter raises if a template forces a key not listed here,
# so a typo in TEMPLATES fails loudly instead of silently adding a column.
FIELDNAMES = ["object_id", "object_type", "amount", "vendor", "ramp_entity", "date", "raw_error"]

# (how many, raw error text, values forced for this error)
# Error text is quoted from the Ramp help article linked in each row of data/catalog.csv.
TEMPLATES = [
    (25, "Could not determine the correct NetSuite Subsidiary for this bill. "
         "Ensure this entity is associated with a NetSuite subsidiary within "
         "your Ramp Accounting Settings.", {"ramp_entity": "Northwind UK"}),
    (12, "The accounting period is closed in your accounting provider. "
         "Please open the period or change the accounting date to fall within "
         "an open period.", {"date": "2026-10-30"}),
    (8, "Please enter value(s) for: Location", {}),
    # 1482 is Gusto's NetSuite internal ID, the same one pre-flight uses in Step 7.
    (6, "We weren't able to sync across the following transaction, as it appears "
        "the account (1482) you chose is not a valid selection in NetSuite.",
        {"vendor": "Gusto"}),
    (5, "Unauthorized user", {}),
    (2, "Invalid Reference Id | Invalid Reference Id : Accounts element id [6120].", {}),
    (2, "Please enter value(s) for: Primary Subsidiary", {"vendor": "Uline"}),
]

rows, n = [], 1
for count, template, forced in TEMPLATES:
    for _ in range(count):
        row = {
            "object_id": f"RMP-{n:04d}",
            "object_type": random.choice(TYPES),
            "amount": round(random.uniform(40, 9000), 2),
            "vendor": random.choice(VENDORS),
            "ramp_entity": random.choice(ENTITIES),
            "date": (date(2026, 11, 1) + timedelta(days=random.randint(0, 19))).isoformat(),
        }
        row.update(forced)
        row["raw_error"] = template.format(**row)
        rows.append(row)
        n += 1

random.shuffle(rows)  # real failure logs are not sorted by cause
out = Path("data/sample_failures.csv")
with out.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} rows to {out}")
