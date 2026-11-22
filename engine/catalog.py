import re
import pandas as pd

COLUMNS = ["id", "category", "owner", "error_pattern", "example_error",
           "cause", "fix_steps", "ramp_url", "group_key"]


def load_catalog(path="data/catalog.csv") -> pd.DataFrame:
    cat = pd.read_csv(path, dtype=str).fillna("")
    missing = set(COLUMNS) - set(cat.columns)
    if missing:
        raise ValueError(f"catalog.csv is missing columns: {missing}")
    if cat["id"].duplicated().any():
        raise ValueError("catalog.csv has duplicate ids")
    # Compile once. Blank patterns are pre-flight-only rows.
    cat["regex"] = cat["error_pattern"].apply(
        lambda p: re.compile(p, re.IGNORECASE) if p else None
    )
    return cat
