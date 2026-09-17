"""
Validate the star schema:
- dimension keys are unique
- fact FKs have no orphans
"""
import pandas as pd
from config import PROCESSED_DIR

STAR_DIR = PROCESSED_DIR.parent / "star_schema"


def load(name):
    df = pd.read_csv(STAR_DIR / f"{name}.csv")
    df.attrs["name"] = name
    return df


def check_unique(df, key):
    dupes = int(df[key].duplicated().sum())
    status = "OK  " if dupes == 0 else f"FAIL"
    print(f"  [{status}] {df.attrs['name']}.{key} unique ({dupes} dupes)")


def check_fk(fact, fk, dim, dim_key):
    missing = set(fact[fk].dropna().unique()) - set(dim[dim_key].dropna().unique())
    status = "OK  " if not missing else "FAIL"
    print(f"  [{status}] {fact.attrs['name']}.{fk} -> {dim.attrs['name']}.{dim_key} "
          f"({len(missing)} orphans)")


def main():
    names = ["dim_patient", "dim_date", "dim_facility", "dim_department",
             "dim_provider", "dim_encounter_type", "dim_diagnosis",
             "dim_lab", "dim_medication", "dim_payer",
             "fact_encounter", "fact_diagnosis", "fact_lab",
             "fact_vitals", "fact_medication", "fact_claim"]
    t = {n: load(n) for n in names}

    print("-- Dimension key uniqueness --")
    for dim, key in [("dim_patient", "patient_key"), ("dim_date", "date_key"),
                     ("dim_facility", "facility_key"), ("dim_department", "department_key"),
                     ("dim_provider", "provider_key"), ("dim_encounter_type", "encounter_type_key"),
                     ("dim_diagnosis", "diagnosis_key"), ("dim_lab", "lab_key"),
                     ("dim_medication", "medication_key"), ("dim_payer", "payer_key")]:
        check_unique(t[dim], key)

    print("\n-- Referential integrity --")
    check_fk(t["fact_encounter"], "patient_key", t["dim_patient"], "patient_key")
    check_fk(t["fact_encounter"], "facility_key", t["dim_facility"], "facility_key")
    check_fk(t["fact_encounter"], "department_key", t["dim_department"], "department_key")
    check_fk(t["fact_encounter"], "provider_key", t["dim_provider"], "provider_key")
    check_fk(t["fact_encounter"], "encounter_type_key", t["dim_encounter_type"], "encounter_type_key")
    check_fk(t["fact_encounter"], "admit_date_key", t["dim_date"], "date_key")

    check_fk(t["fact_diagnosis"], "diagnosis_key", t["dim_diagnosis"], "diagnosis_key")
    check_fk(t["fact_diagnosis"], "patient_key", t["dim_patient"], "patient_key")

    check_fk(t["fact_lab"], "lab_key", t["dim_lab"], "lab_key")
    check_fk(t["fact_lab"], "patient_key", t["dim_patient"], "patient_key")

    check_fk(t["fact_vitals"], "patient_key", t["dim_patient"], "patient_key")

    check_fk(t["fact_medication"], "medication_key", t["dim_medication"], "medication_key")
    check_fk(t["fact_medication"], "patient_key", t["dim_patient"], "patient_key")

    check_fk(t["fact_claim"], "payer_key", t["dim_payer"], "payer_key")
    check_fk(t["fact_claim"], "patient_key", t["dim_patient"], "patient_key")

    print("\nDone.")


if __name__ == "__main__":
    main()