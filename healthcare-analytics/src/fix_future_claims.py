"""
Cap future-dated claims to the max in-range fact date.
Keeps referential integrity to dim_date intact.
"""
import pandas as pd
from config import PROCESSED_DIR

STAR_DIR = PROCESSED_DIR.parent / "star_schema"
TODAY_KEY = int(pd.Timestamp.today().strftime("%Y%m%d"))

clm = pd.read_csv(STAR_DIR / "fact_claim.csv")
before = (clm["date_key"] > TODAY_KEY).sum()
clm.loc[clm["date_key"] > TODAY_KEY, "date_key"] = TODAY_KEY
clm.to_csv(STAR_DIR / "fact_claim.csv", index=False)
print(f"Capped {before} future-dated claims to {TODAY_KEY}")

# Now re-trim dim_date
enc = pd.read_csv(STAR_DIR / "fact_encounter.csv")
lab = pd.read_csv(STAR_DIR / "fact_lab.csv")
keys = pd.concat([
    enc["admit_date_key"], enc["discharge_date_key"],
    lab["date_key"], clm["date_key"]
]).dropna().astype(int)

dim = pd.read_csv(STAR_DIR / "dim_date.csv")
dim = dim[(dim["date_key"] >= keys.min()) & (dim["date_key"] <= keys.max())]
dim.to_csv(STAR_DIR / "dim_date.csv", index=False)
print(f"dim_date: {len(dim)} rows, {keys.min()} -> {keys.max()}")