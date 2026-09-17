from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"

for d in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
N_PATIENTS = 500
N_ENCOUNTERS = 1500

# ICD-10 reference (subset)
ICD10_LOOKUP = {
    "E11.9": "Type 2 diabetes mellitus without complications",
    "I10":   "Essential (primary) hypertension",
    "J44.9": "Chronic obstructive pulmonary disease, unspecified",
    "N18.3": "Chronic kidney disease, stage 3 (moderate)",
    "I50.9": "Heart failure, unspecified",
    "E78.5": "Hyperlipidemia, unspecified",
    "F32.9": "Major depressive disorder, single episode, unspecified",
    "Z79.4": "Long term (current) use of insulin",
    "J45.909": "Unspecified asthma, uncomplicated",
    "K21.9": "Gastro-esophageal reflux disease without esophagitis",
}

# Common ICD-9 to ICD-10 crosswalk (for the messy file)
ICD9_TO_ICD10 = {
    "250.00": "E11.9",
    "401.9":  "I10",
    "496":    "J44.9",
    "585.3":  "N18.3",
    "428.0":  "I50.9",
    "272.4":  "E78.5",
    "311":    "F32.9",
    "V58.67": "Z79.4",
}

# LOINC reference
LOINC_LOOKUP = {
    "4548-4": ("Hemoglobin A1c", "%", 4.0, 5.6),
    "2160-0": ("Creatinine", "mg/dL", 0.6, 1.3),
    "718-7":  ("Hemoglobin", "g/dL", 12.0, 17.5),
    "6690-2": ("Leukocytes", "10^3/uL", 4.0, 11.0),
    "2951-2": ("Sodium", "mmol/L", 135, 145),
    "2823-3": ("Potassium", "mmol/L", 3.5, 5.1),
    "2345-7": ("Glucose", "mg/dL", 70, 99),
}

# RxNorm
RXNORM_LOOKUP = {
    "860975": "Metformin 500 MG Oral Tablet",
    "314076": "Lisinopril 10 MG Oral Tablet",
    "617312": "Atorvastatin 20 MG Oral Tablet",
    "197361": "Amlodipine 5 MG Oral Tablet",
    "866924": "Metoprolol Succinate 25 MG Oral Tablet",
}

FACILITIES = [
    "Mercy General Hospital",
    "St. Luke's Medical Center",
    "Riverside Community Hospital",
    "Northside Regional Medical Center",
]

DEPARTMENTS = ["Internal Medicine", "Cardiology", "Endocrinology",
               "Pulmonology", "Nephrology", "Psychiatry", "Emergency"]

PAYERS = ["Medicare", "Medicaid", "BlueCross", "Aetna", "United",
          "Cigna", "Self-Pay", "Other"]

RACES = ["White", "Black or African American", "Asian",
         "American Indian or Alaska Native", "Native Hawaiian or Pacific Islander",
         "Other", "Unknown"]

ETHNICITIES = ["Hispanic or Latino", "Not Hispanic or Latino", "Unknown"]

ENCOUNTER_TYPES = ["Inpatient", "Outpatient", "Emergency", "Observation"]