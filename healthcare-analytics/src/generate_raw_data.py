"""
Generate a realistic, intentionally messy synthetic EHR dataset.
Outputs CSVs to data/raw/.
"""
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
from tqdm import tqdm

from config import (RAW_DIR, RANDOM_SEED, N_PATIENTS, N_ENCOUNTERS,
                    ICD10_LOOKUP, ICD9_TO_ICD10, LOINC_LOOKUP, RXNORM_LOOKUP,
                    FACILITIES, DEPARTMENTS, PAYERS, RACES, ETHNICITIES,
                    ENCOUNTER_TYPES)

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------
def generate_patients(n=N_PATIENTS):
    rows = []
    for i in range(n):
        dob = fake.date_of_birth(minimum_age=0, maximum_age=95)
        sex = random.choice(["M", "F"])
        # ~8% missing race, ~10% missing ethnicity
        race = random.choice(RACES) if random.random() > 0.08 else None
        eth = random.choice(ETHNICITIES) if random.random() > 0.10 else None

        # ~10% of records get inconsistent name formatting (typos / case)
        first = fake.first_name()
        last = fake.last_name()
        if random.random() < 0.10:
            first = first.upper()
        if random.random() < 0.05:
            last = last + " "  # trailing space
        if random.random() < 0.03:
            first = first.replace("a", "@")  # deliberate typo

        rows.append({
            "mrn": f"MRN{100000 + i}",
            "first_name": first,
            "last_name": last,
            "dob": dob,
            "sex": sex,
            "race": race,
            "ethnicity": eth,
            "zip": fake.postcode(),
            "payer": random.choice(PAYERS),
            "language": random.choice(["English", "Spanish", "Other"]),
            "is_test_patient": random.random() < 0.01,  # ~1% test patients
        })

    df = pd.DataFrame(rows)

    # Inject ~5% duplicate patients with slight variation (same MRN or same name+DOB)
    dups = df.sample(frac=0.05, random_state=RANDOM_SEED).copy()
    dups["mrn"] = dups["mrn"] + "-A"           # duplicate MRN suffix
    dups["first_name"] = dups["first_name"].str.lower()
    dups["race"] = None                        # often blank on the dupe
    df = pd.concat([df, dups], ignore_index=True)

    # Random missing DOB (~2%)
    df.loc[df.sample(frac=0.02, random_state=1).index, "dob"] = pd.NaT

    # Mix DOB formats as strings to simulate messy ingestion
    df["dob"] = df["dob"].apply(
        lambda d: d.strftime("%m/%d/%Y") if pd.notna(d) and random.random() > 0.3
        else (d.strftime("%Y-%m-%d") if pd.notna(d) else None)
    )
    return df


# ---------------------------------------------------------------------------
# Encounters
# ---------------------------------------------------------------------------
def generate_encounters(patients, n=N_ENCOUNTERS):
    rows = []
    base = datetime(2023, 1, 1)
    for i in range(n):
        p = patients.sample(1).iloc[0]
        admit = base + timedelta(days=random.randint(0, 730),
                                 hours=random.randint(0, 23))
        etype = random.choice(ENCOUNTER_TYPES)
        los_days = {"Inpatient": random.randint(1, 12),
                    "Observation": random.randint(1, 2),
                    "Emergency": 0,
                    "Outpatient": 0}[etype]
        discharge = admit + timedelta(days=los_days) if los_days else None

        rows.append({
            "encounter_id": f"ENC{200000 + i}",
            "mrn": p["mrn"],
            "admit_dt": admit.strftime("%Y-%m-%d %H:%M:%S"),
            "discharge_dt": discharge.strftime("%Y-%m-%d %H:%M:%S") if discharge else None,
            "encounter_type": etype,
            "facility": random.choice(FACILITIES),
            "department": random.choice(DEPARTMENTS),
            "attending_provider": fake.name(),
            "drg": f"DRG{random.randint(100, 999)}",
        })

    df = pd.DataFrame(rows)

    # ~3% future-dated admits (data entry error)
    bad_idx = df.sample(frac=0.03, random_state=2).index
    df.loc[bad_idx, "admit_dt"] = "2027-01-15 10:00:00"

    # ~2% discharge before admit
    bad_idx2 = df.sample(frac=0.02, random_state=3).index
    df.loc[bad_idx2, "discharge_dt"] = "2020-01-01 08:00:00"

    # ~5% missing discharge_dt for inpatient (real-world)
    ip = df[df["encounter_type"] == "Inpatient"]
    if len(ip):
        df.loc[ip.sample(frac=0.05, random_state=4).index, "discharge_dt"] = None

    return df


# ---------------------------------------------------------------------------
# Diagnoses (mixed ICD-9 and ICD-10)
# ---------------------------------------------------------------------------
def generate_diagnoses(encounters):
    rows = []
    icd10_codes = list(ICD10_LOOKUP.keys())
    icd9_codes = list(ICD9_TO_ICD10.keys())

    for _, e in encounters.iterrows():
        n_dx = random.randint(1, 4)
        for j in range(n_dx):
            use_icd9 = random.random() < 0.15  # legacy codes
            code = random.choice(icd9_codes if use_icd9 else icd10_codes)
            rows.append({
                "encounter_id": e["encounter_id"],
                "mrn": e["mrn"],
                "dx_seq": j + 1,
                "icd_code": code,
                "dx_desc": None,  # to be filled after normalization
                "present_on_admission": random.choice(["Y", "N", "U", None]),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Labs (with unit inconsistencies)
# ---------------------------------------------------------------------------
def generate_labs(encounters):
    rows = []
    loinc_codes = list(LOINC_LOOKUP.keys())
    for _, e in encounters.iterrows():
        if random.random() > 0.6:      # only ~60% of encounters have labs
            continue
        for code in random.sample(loinc_codes, k=random.randint(1, 4)):
            name, unit, low, high = LOINC_LOOKUP[code]
            # 10% of values intentionally out of range
            if random.random() < 0.10:
                val = round(random.uniform(high * 1.1, high * 2), 2)
            else:
                val = round(random.uniform(low, high), 2)

            # Unit inconsistency: 8% chance of alternate unit
            u = unit
            if code == "2345-7" and random.random() < 0.08:
                u = "mmol/L"
                val = round(val / 18.0, 2)  # mg/dL -> mmol/L
            if code == "2160-0" and random.random() < 0.05:
                u = "umol/L"
                val = round(val * 88.4, 1)

            rows.append({
                "encounter_id": e["encounter_id"],
                "mrn": e["mrn"],
                "loinc": code,
                "result_name": name,
                "value": val,
                "unit": u,
                "collected_dt": e["admit_dt"],
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Vitals
# ---------------------------------------------------------------------------
def generate_vitals(encounters):
    rows = []
    for _, e in encounters.iterrows():
        if random.random() > 0.7:
            continue
        # BP as messy string
        sbp = random.randint(95, 175)
        dbp = random.randint(55, 105)
        bp_fmt = random.random()
        if bp_fmt < 0.6:
            bp = f"{sbp}/{dbp}"
        elif bp_fmt < 0.8:
            bp = f"{sbp} / {dbp}"
        else:
            bp = f"SBP {sbp}, DBP {dbp}"

        # Temp in F or C
        if random.random() < 0.7:
            temp = round(random.uniform(97.0, 101.0), 1)
            temp_unit = "F"
        else:
            temp = round(random.uniform(36.0, 38.5), 1)
            temp_unit = "C"

        # Weight in lbs or kg
        if random.random() < 0.5:
            weight = round(random.uniform(110, 260), 1)
            weight_unit = "lb"
        else:
            weight = round(random.uniform(50, 118), 1)
            weight_unit = "kg"

        rows.append({
            "encounter_id": e["encounter_id"],
            "mrn": e["mrn"],
            "bp": bp,
            "hr": random.randint(55, 120),
            "temp": temp,
            "temp_unit": temp_unit,
            "weight": weight,
            "weight_unit": weight_unit,
            "height_cm": round(random.uniform(150, 195), 1),
            "spo2": random.randint(88, 100),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------
def generate_medications(encounters):
    rows = []
    rx_codes = list(RXNORM_LOOKUP.keys())
    for _, e in encounters.iterrows():
        if random.random() > 0.55:
            continue
        for code in random.sample(rx_codes, k=random.randint(1, 3)):
            rows.append({
                "encounter_id": e["encounter_id"],
                "mrn": e["mrn"],
                "rxnorm": code,
                "med_name": RXNORM_LOOKUP[code],
                "dose": random.choice(["1 tablet", "2 tablets", "0.5 tablet"]),
                "frequency": random.choice(["QD", "BID", "TID", "QHS", "PRN"]),
                "start_dt": e["admit_dt"],
                "stop_dt": e["discharge_dt"],
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------
def generate_claims(encounters, patients):
    rows = []
    for _, e in encounters.iterrows():
        billed = round(random.uniform(500, 45000), 2)
        paid = round(billed * random.uniform(0.4, 0.95), 2)
        denial = random.choice(["", "", "", "CO-16", "CO-97", "PR-1", "CO-50"])
        rows.append({
            "claim_id": f"CLM{e['encounter_id'][3:]}",
            "encounter_id": e["encounter_id"],
            "mrn": e["mrn"],
            "payer": patients.loc[patients["mrn"] == e["mrn"], "payer"].iloc[0]
                     if (patients["mrn"] == e["mrn"]).any() else "Unknown",
            "billed_amt": billed,
            "paid_amt": paid if not denial else 0.0,
            "denial_code": denial or None,
            "submitted_dt": e["admit_dt"],
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Generating patients...")
    patients = generate_patients()
    patients.to_csv(RAW_DIR / "patients_raw.csv", index=False)

    print("Generating encounters...")
    encounters = generate_encounters(patients)
    encounters.to_csv(RAW_DIR / "encounters_raw.csv", index=False)

    print("Generating diagnoses...")
    dx = generate_diagnoses(encounters)
    dx.to_csv(RAW_DIR / "diagnoses_raw.csv", index=False)

    print("Generating labs...")
    labs = generate_labs(encounters)
    labs.to_csv(RAW_DIR / "labs_raw.csv", index=False)

    print("Generating vitals...")
    vitals = generate_vitals(encounters)
    vitals.to_csv(RAW_DIR / "vitals_raw.csv", index=False)

    print("Generating medications...")
    meds = generate_medications(encounters)
    meds.to_csv(RAW_DIR / "medications_raw.csv", index=False)

    print("Generating claims...")
    claims = generate_claims(encounters, patients)
    claims.to_csv(RAW_DIR / "claims_raw.csv", index=False)

    print("\nRaw data written to:", RAW_DIR)
    print(f"Patients: {len(patients)} | Encounters: {len(encounters)} | "
          f"Dx: {len(dx)} | Labs: {len(labs)} | Vitals: {len(vitals)} | "
          f"Meds: {len(meds)} | Claims: {len(claims)}")


if __name__ == "__main__":
    main()