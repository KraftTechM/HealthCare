"""
Clean and normalize the raw healthcare dataset.
Outputs normalized tables to data/processed/.
"""
import re
import numpy as np
import pandas as pd
from dateutil import parser as dtparse

from config import (RAW_DIR, PROCESSED_DIR,
                    ICD10_LOOKUP, ICD9_TO_ICD10, LOINC_LOOKUP, RXNORM_LOOKUP)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def parse_dt_safe(x):
    if pd.isna(x) or x in ("", None):
        return pd.NaT
    try:
        return dtparse.parse(str(x))
    except Exception:
        return pd.NaT


def standardize_name(s):
    if pd.isna(s):
        return s
    s = str(s).strip().title()
    s = s.replace("@", "a")           # fix synthetic typo
    s = re.sub(r"\s+", " ", s)
    return s


def standardize_sex(x):
    if pd.isna(x):
        return None
    v = str(x).strip().upper()
    if v in {"M", "MALE"}:
        return "Male"
    if v in {"F", "FEMALE"}:
        return "Female"
    return "Other/Unknown"


def standardize_race(x):
    if pd.isna(x) or str(x).strip().lower() in {"", "unknown", "nan"}:
        return "Unknown"
    mapping = {
        "white": "White",
        "black or african american": "Black or African American",
        "black": "Black or African American",
        "asian": "Asian",
        "american indian or alaska native": "American Indian or Alaska Native",
        "native hawaiian or pacific islander": "Native Hawaiian or Pacific Islander",
        "other": "Other",
    }
    return mapping.get(str(x).strip().lower(), "Other")


def standardize_ethnicity(x):
    if pd.isna(x) or str(x).strip().lower() in {"", "unknown", "nan"}:
        return "Unknown"
    v = str(x).strip().lower()
    if "hispanic" in v and "not" not in v:
        return "Hispanic or Latino"
    if "not hispanic" in v:
        return "Not Hispanic or Latino"
    return "Unknown"


def parse_bp(bp):
    """Return (systolic, diastolic) as ints, or (None, None)."""
    if pd.isna(bp):
        return None, None
    s = str(bp)
    m = re.search(r"(\d{2,3})\s*[/,]\s*(\d{2,3})", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"SBP\s*(\d+).*DBP\s*(\d+)", s, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def f_to_c(f):
    return round((f - 32) * 5.0 / 9.0, 2) if pd.notna(f) else np.nan


def lb_to_kg(lb):
    return round(lb * 0.45359237, 2) if pd.notna(lb) else np.nan


def bmi(weight_kg, height_cm):
    if pd.isna(weight_kg) or pd.isna(height_cm) or height_cm == 0:
        return np.nan
    h = height_cm / 100.0
    return round(weight_kg / (h * h), 1)


# ---------------------------------------------------------------------------
# Table-specific cleaners
# ---------------------------------------------------------------------------
def clean_patients(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["first_name"] = df["first_name"].apply(standardize_name)
    df["last_name"] = df["last_name"].apply(standardize_name)
    df["dob"] = df["dob"].apply(parse_dt_safe)
    df["sex"] = df["sex"].apply(standardize_sex)
    df["race"] = df["race"].apply(standardize_race)
    df["ethnicity"] = df["ethnicity"].apply(standardize_ethnicity)
    df["payer"] = df["payer"].str.strip().str.title()

    # Drop test patients
    df = df[df["is_test_patient"] != True].drop(columns=["is_test_patient"])

    # Deduplicate: normalize MRN (strip "-A" suffix)
    df["mrn_clean"] = df["mrn"].str.replace(r"-\w+$", "", regex=True)
    df = df.sort_values("mrn_clean")

    # Prefer row with fewer nulls for each mrn_clean
    df["_nulls"] = df.isna().sum(axis=1)
    df = (df.sort_values(["mrn_clean", "_nulls"])
            .drop_duplicates(subset="mrn_clean", keep="first")
            .drop(columns=["_nulls", "mrn"])
            .rename(columns={"mrn_clean": "mrn"}))

    # Derived: age
    today = pd.Timestamp.today().normalize()
    df["age"] = ((today - df["dob"]).dt.days / 365.25).round(0)
    df["age_band"] = pd.cut(df["age"],
                            bins=[-1, 17, 39, 64, 200],
                            labels=["0-17", "18-39", "40-64", "65+"])
    return df.reset_index(drop=True)


def clean_encounters(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["admit_dt"] = df["admit_dt"].apply(parse_dt_safe)
    df["discharge_dt"] = df["discharge_dt"].apply(parse_dt_safe)

    # Remove future-dated admits (data entry errors)
    today = pd.Timestamp.today().normalize()
    df = df[df["admit_dt"] <= today]

    # Fix discharge < admit
    bad = df["discharge_dt"] < df["admit_dt"]
    df.loc[bad, "discharge_dt"] = pd.NaT

    # Length of stay (days)
    los = (df["discharge_dt"] - df["admit_dt"]).dt.total_seconds() / 86400.0
    df["los_days"] = los.round(2)

    # Flag: still inpatient (no discharge but inpatient type)
    df["is_current_inpatient"] = (
        df["encounter_type"].eq("Inpatient") & df["discharge_dt"].isna()
    )
    return df.reset_index(drop=True)


def clean_diagnoses(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Convert ICD-9 -> ICD-10
    df["icd_code_std"] = df["icd_code"].apply(
        lambda c: ICD9_TO_ICD10.get(str(c).strip(), str(c).strip())
    )
    df["icd_system"] = df["icd_code"].apply(
        lambda c: "ICD-9" if str(c).strip() in ICD9_TO_ICD10 else "ICD-10"
    )
    df["dx_desc"] = df["icd_code_std"].map(ICD10_LOOKUP).fillna("Unknown code")
    df["present_on_admission"] = df["present_on_admission"].fillna("U")
    return df


def clean_labs(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Convert alternate units back to canonical units
    def convert(row):
        code, v, u = row["loinc"], row["value"], row["unit"]
        if pd.isna(v):
            return v, u
        if code == "2345-7" and u == "mmol/L":
            return round(v * 18.0, 2), "mg/dL"
        if code == "2160-0" and u == "umol/L":
            return round(v / 88.4, 2), "mg/dL"
        return v, u

    fixed = df.apply(convert, axis=1, result_type="expand")
    df["value"], df["unit"] = fixed[0], fixed[1]

    # Reference range + abnormal flag
    ref = df["loinc"].map(lambda c: LOINC_LOOKUP.get(c, (None, None, None, None)))
    df["ref_low"] = ref.apply(lambda t: t[2])
    df["ref_high"] = ref.apply(lambda t: t[3])
    df["abnormal_flag"] = np.where(
        df["value"].isna() | df["ref_low"].isna(), "Unknown",
        np.where(df["value"] < df["ref_low"], "Low",
        np.where(df["value"] > df["ref_high"], "High", "Normal"))
    )
    df["collected_dt"] = df["collected_dt"].apply(parse_dt_safe)
    return df


def clean_vitals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    parsed = df["bp"].apply(parse_bp)
    df["systolic"] = parsed.apply(lambda t: t[0])
    df["diastolic"] = parsed.apply(lambda t: t[1])

    # Drop physiologically implausible BP
    df.loc[(df["systolic"] < 50) | (df["systolic"] > 260), "systolic"] = np.nan
    df.loc[(df["diastolic"] < 30) | (df["diastolic"] > 160), "diastolic"] = np.nan

    # Normalize temperature to Celsius
    df["temp_c"] = np.where(df["temp_unit"] == "F",
                            df["temp"].apply(f_to_c),
                            df["temp"])

    # Normalize weight to kg
    df["weight_kg"] = np.where(df["weight_unit"].str.lower() == "lb",
                               df["weight"].apply(lb_to_kg),
                               df["weight"])

    df["bmi"] = [bmi(w, h) for w, h in zip(df["weight_kg"], df["height_cm"])]

    return df.drop(columns=["bp", "temp", "temp_unit",
                            "weight", "weight_unit"])


def clean_medications(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["med_name"] = df["rxnorm"].map(RXNORM_LOOKUP).fillna(df["med_name"])
    df["start_dt"] = df["start_dt"].apply(parse_dt_safe)
    df["stop_dt"] = df["stop_dt"].apply(parse_dt_safe)
    return df


def clean_claims(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["submitted_dt"] = df["submitted_dt"].apply(parse_dt_safe)
    df["billed_amt"] = pd.to_numeric(df["billed_amt"], errors="coerce")
    df["paid_amt"] = pd.to_numeric(df["paid_amt"], errors="coerce")
    df["denied"] = df["denial_code"].notna()
    df["reimbursement_rate"] = (df["paid_amt"] / df["billed_amt"]).round(3)
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
CLEANERS = {
    "patients": clean_patients,
    "encounters": clean_encounters,
    "diagnoses": clean_diagnoses,
    "labs": clean_labs,
    "vitals": clean_vitals,
    "medications": clean_medications,
    "claims": clean_claims,
}


def main():
    for name, fn in CLEANERS.items():
        raw = pd.read_csv(RAW_DIR / f"{name}_raw.csv")
        clean = fn(raw)
        out = PROCESSED_DIR / f"{name}.csv"
        clean.to_csv(out, index=False)
        print(f"[OK] {name:<12} {len(raw):>6} -> {len(clean):>6} rows  ->  {out.name}")


if __name__ == "__main__":
    main()