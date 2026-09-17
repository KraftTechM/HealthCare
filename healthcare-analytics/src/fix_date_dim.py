"""
Trim dim_date to the range of actual fact activity.
Removes empty years that pollute Power BI slicers.
"""
import pandas as pd
from config import PROCESSED_DIR

STAR_DIR = PROCESSED_DIR.parent / "star_schema"

# Load facts that reference dates
enc = pd.read_csv(STAR_DIR / "fact_encounter.csv")
lab = pd.read_csv(STAR_DIR / "fact_lab.csv")
clm = pd.read_csv(STAR_DIR / "fact_claim.csv")

keys = pd.concat([
    enc["admit_date_key"], enc["discharge_date_key"],
    lab["date_key"], clm["date_key"]
]).dropna().astype(int)

min_key, max_key = keys.min(), keys.max()
print(f"Fact date range: {min_key} -> {max_key}")

dim = pd.read_csv(STAR_DIR / "dim_date.csv")
before = len(dim)
dim = dim[(dim["date_key"] >= min_key) & (dim["date_key"] <= max_key)]
dim.to_csv(STAR_DIR / "dim_date.csv", index=False)
print(f"dim_date trimmed: {before} -> {len(dim)} rows")