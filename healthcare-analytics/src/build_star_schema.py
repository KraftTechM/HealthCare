"""
Build star schema (dim + fact tables) from normalized data.
Creates surrogate keys for all dimensions and wires facts to dims.
Writes to data/star_schema/.
"""
import pandas as pd
import numpy as np
from config import PROCESSED_DIR

STAR_DIR = PROCESSED_DIR.parent / "star_schema"
STAR_DIR.mkdir(parents=True, exist_ok=True)


# ---------- helpers ----------
def to_date_key(dt_series):
    """Convert datetime series to YYYYMMDD integer key, NA if missing."""
    dt = pd.to_datetime(dt_series, errors="coerce")
    keys = dt.dt.strftime("%Y%m%d")
    return keys.where(dt.notna(), pd.NA).astype("Int64")


def build_dim_lookup(df, natural_col, key_name, extra_cols=None):
    cols = [natural_col] + (extra_cols or [])
    dim = df[cols].drop_duplicates(subset=[natural_col]).reset_index(drop=True)
    dim.insert(0, key_name, range(1, len(dim) + 1))
    return dim


# ---------- load ----------
def load():
    files = ["patients", "encounters", "diagnoses", "labs",
             "vitals", "medications", "claims"]
    data = {f: pd.read_csv(PROCESSED_DIR / f"{f}.csv") for f in files}

    data["encounters"]["admit_dt"] = pd.to_datetime(data["encounters"]["admit_dt"], errors="coerce")
    data["encounters"]["discharge_dt"] = pd.to_datetime(data["encounters"]["discharge_dt"], errors="coerce")
    data["labs"]["collected_dt"] = pd.to_datetime(data["labs"]["collected_dt"], errors="coerce")
    data["medications"]["start_dt"] = pd.to_datetime(data["medications"]["start_dt"], errors="coerce")
    data["medications"]["stop_dt"] = pd.to_datetime(data["medications"]["stop_dt"], errors="coerce")
    data["claims"]["submitted_dt"] = pd.to_datetime(data["claims"]["submitted_dt"], errors="coerce")
    return data


# ---------- dimensions ----------
def build_dim_patient(patients):
    df = patients.copy()
    df.insert(0, "patient_key", range(1, len(df) + 1))
    keep = ["patient_key", "mrn", "first_name", "last_name", "dob",
            "sex", "race", "ethnicity", "zip", "payer", "language",
            "age", "age_band"]
    return df[[c for c in keep if c in df.columns]]


def build_dim_date(min_dt, max_dt):
    days = pd.date_range(min_dt, max_dt, freq="D")
    df = pd.DataFrame({"date": days})
    df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["day"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.dayofweek + 1
    df["day_name"] = df["date"].dt.strftime("%a")
    df["is_weekend"] = df["day_of_week"].isin([6, 7])
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    return df[["date_key", "date", "year", "quarter", "month", "month_name",
               "day", "day_of_week", "day_name", "is_weekend", "year_month"]]


def build_dims(data):
    dims = {}
    dims["dim_patient"] = build_dim_patient(data["patients"])
    dims["dim_facility"] = build_dim_lookup(data["encounters"], "facility", "facility_key")
    dims["dim_department"] = build_dim_lookup(data["encounters"], "department", "department_key")
    dims["dim_provider"] = build_dim_lookup(data["encounters"], "attending_provider", "provider_key")
    dims["dim_encounter_type"] = build_dim_lookup(data["encounters"], "encounter_type", "encounter_type_key")
    dims["dim_payer"] = build_dim_lookup(data["patients"], "payer", "payer_key")

    dim_dx = (data["diagnoses"][["icd_code_std", "dx_desc", "icd_system"]]
              .drop_duplicates(subset=["icd_code_std"])
              .reset_index(drop=True))
    dim_dx.insert(0, "diagnosis_key", range(1, len(dim_dx) + 1))
    dims["dim_diagnosis"] = dim_dx

    dim_lab = (data["labs"][["loinc", "result_name", "unit", "ref_low", "ref_high"]]
               .drop_duplicates(subset=["loinc"])
               .reset_index(drop=True))
    dim_lab.insert(0, "lab_key", range(1, len(dim_lab) + 1))
    dims["dim_lab"] = dim_lab

    dim_med = (data["medications"][["rxnorm", "med_name"]]
               .drop_duplicates(subset=["rxnorm"])
               .reset_index(drop=True))
    dim_med.insert(0, "medication_key", range(1, len(dim_med) + 1))
    dims["dim_medication"] = dim_med
    return dims


# ---------- facts ----------
def build_facts(data, dims):
    facts = {}

    # --- lookup maps: natural key -> surrogate key
    patient_map = dict(zip(dims["dim_patient"]["mrn"], dims["dim_patient"]["patient_key"]))
    facility_map = dict(zip(dims["dim_facility"]["facility"], dims["dim_facility"]["facility_key"]))
    dept_map = dict(zip(dims["dim_department"]["department"], dims["dim_department"]["department_key"]))
    prov_map = dict(zip(dims["dim_provider"]["attending_provider"], dims["dim_provider"]["provider_key"]))
    type_map = dict(zip(dims["dim_encounter_type"]["encounter_type"], dims["dim_encounter_type"]["encounter_type_key"]))
    payer_map = dict(zip(dims["dim_payer"]["payer"], dims["dim_payer"]["payer_key"]))
    dx_map = dict(zip(dims["dim_diagnosis"]["icd_code_std"], dims["dim_diagnosis"]["diagnosis_key"]))
    lab_map = dict(zip(dims["dim_lab"]["loinc"], dims["dim_lab"]["lab_key"]))
    med_map = dict(zip(dims["dim_medication"]["rxnorm"], dims["dim_medication"]["medication_key"]))

    # --- fact_encounter
    enc = data["encounters"].copy()
    enc["patient_key"] = enc["mrn"].map(patient_map).astype("Int64")
    enc["facility_key"] = enc["facility"].map(facility_map).astype("Int64")
    enc["department_key"] = enc["department"].map(dept_map).astype("Int64")
    enc["provider_key"] = enc["attending_provider"].map(prov_map).astype("Int64")
    enc["encounter_type_key"] = enc["encounter_type"].map(type_map).astype("Int64")
    enc["admit_date_key"] = to_date_key(enc["admit_dt"])
    enc["discharge_date_key"] = to_date_key(enc["discharge_dt"])

    facts["fact_encounter"] = enc[[
        "encounter_id", "patient_key", "admit_date_key", "discharge_date_key",
        "facility_key", "department_key", "provider_key", "encounter_type_key",
        "los_days", "is_current_inpatient", "drg"
    ]].copy()

    enc_dates = enc.set_index("encounter_id")["admit_date_key"]

    # --- fact_diagnosis
    dx = data["diagnoses"].copy()
    dx["patient_key"] = dx["mrn"].map(patient_map).astype("Int64")
    dx["diagnosis_key"] = dx["icd_code_std"].map(dx_map).astype("Int64")
    dx["date_key"] = dx["encounter_id"].map(enc_dates)
    facts["fact_diagnosis"] = dx[[
        "encounter_id", "patient_key", "diagnosis_key", "date_key",
        "dx_seq", "present_on_admission"
    ]].copy()

    # --- fact_lab
    lab = data["labs"].copy()
    lab["patient_key"] = lab["mrn"].map(patient_map).astype("Int64")
    lab["lab_key"] = lab["loinc"].map(lab_map).astype("Int64")
    lab["date_key"] = to_date_key(lab["collected_dt"])
    lab.insert(0, "lab_fact_id", range(1, len(lab) + 1))
    facts["fact_lab"] = lab[[
        "lab_fact_id", "encounter_id", "patient_key", "lab_key", "date_key",
        "value", "abnormal_flag"
    ]].copy()

    # --- fact_vitals
    vit = data["vitals"].copy()
    vit["patient_key"] = vit["mrn"].map(patient_map).astype("Int64")
    vit["date_key"] = vit["encounter_id"].map(enc_dates)
    vit.insert(0, "vital_fact_id", range(1, len(vit) + 1))
    facts["fact_vitals"] = vit[[
        "vital_fact_id", "encounter_id", "patient_key", "date_key",
        "systolic", "diastolic", "hr", "temp_c", "weight_kg",
        "height_cm", "bmi", "spo2"
    ]].copy()

    # --- fact_medication
    md = data["medications"].copy()
    md["patient_key"] = md["mrn"].map(patient_map).astype("Int64")
    md["medication_key"] = md["rxnorm"].map(med_map).astype("Int64")
    md["start_date_key"] = to_date_key(md["start_dt"])
    md["stop_date_key"] = to_date_key(md["stop_dt"])
    md.insert(0, "med_fact_id", range(1, len(md) + 1))
    facts["fact_medication"] = md[[
        "med_fact_id", "encounter_id", "patient_key", "medication_key",
        "start_date_key", "stop_date_key", "dose", "frequency"
    ]].copy()

    # --- fact_claim
    cl = data["claims"].copy()
    cl["patient_key"] = cl["mrn"].map(patient_map).astype("Int64")
    cl["payer_key"] = cl["payer"].map(payer_map).astype("Int64")
    cl["date_key"] = to_date_key(cl["submitted_dt"])
    facts["fact_claim"] = cl[[
        "claim_id", "encounter_id", "patient_key", "payer_key", "date_key",
        "billed_amt", "paid_amt", "denial_code", "denied", "reimbursement_rate"
    ]].copy()

    return facts


# ---------- main ----------
def main():
    print("Loading normalized data...")
    data = load()

    print("Building dimensions...")
    dims = build_dims(data)

    all_dates = pd.concat([
        data["encounters"]["admit_dt"],
        data["encounters"]["discharge_dt"],
        data["labs"]["collected_dt"],
        data["medications"]["start_dt"],
        data["medications"]["stop_dt"],
        data["claims"]["submitted_dt"],
    ]).dropna()
    dims["dim_date"] = build_dim_date(all_dates.min().normalize(),
                                      all_dates.max().normalize())

    print("Building fact tables...")
    facts = build_facts(data, dims)

    print(f"\nWriting star schema to: {STAR_DIR}")
    all_tables = {**dims, **facts}
    for name, df in all_tables.items():
        df.to_csv(STAR_DIR / f"{name}.csv", index=False)
        print(f"  {name:<22} {len(df):>7} rows x {df.shape[1]:>2} cols")

    print(f"\nDone. {len(dims)} dimensions, {len(facts)} facts.")


if __name__ == "__main__":
    main()