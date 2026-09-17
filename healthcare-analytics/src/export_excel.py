"""
Export normalized tables to a single, well-structured Excel workbook.
"""
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils.dataframe import dataframe_to_rows

from config import PROCESSED_DIR, REPORTS_DIR

OUT = REPORTS_DIR / "healthcare_normalized.xlsx"

TABLES = ["patients", "encounters", "diagnoses", "labs",
          "vitals", "medications", "claims"]

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def write_table(ws, df: pd.DataFrame):
    ws.append(list(df.columns))
    for row in dataframe_to_rows(df, index=False, header=False):
        ws.append(row)
    for c in ws[1]:
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(horizontal="center")
    for col_cells in ws.columns:
        max_len = max(len(str(c.value)) if c.value is not None else 0
                      for c in col_cells[:200])
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 3, 40)


def add_data_dictionary(wb):
    dd = [
        ("patients", "mrn", "Medical record number (unique, deduplicated)"),
        ("patients", "first_name", "Standardized first name (title case)"),
        ("patients", "last_name", "Standardized last name"),
        ("patients", "dob", "Date of birth (ISO)"),
        ("patients", "sex", "Male / Female / Other-Unknown"),
        ("patients", "race", "Standardized race category"),
        ("patients", "ethnicity", "Hispanic or Latino / Not Hispanic or Latino / Unknown"),
        ("patients", "age", "Age in years (derived)"),
        ("patients", "age_band", "0-17 / 18-39 / 40-64 / 65+"),
        ("encounters", "encounter_id", "Unique encounter identifier"),
        ("encounters", "encounter_type", "Inpatient / Outpatient / Emergency / Observation"),
        ("encounters", "admit_dt", "Admission timestamp (ISO)"),
        ("encounters", "discharge_dt", "Discharge timestamp (ISO)"),
        ("encounters", "los_days", "Length of stay in days (derived)"),
        ("diagnoses", "icd_code_std", "ICD-10 code (ICD-9 auto-mapped)"),
        ("diagnoses", "icd_system", "Original code system (ICD-9 / ICD-10)"),
        ("diagnoses", "present_on_admission", "Y / N / U"),
        ("labs", "loinc", "LOINC code"),
        ("labs", "value", "Numeric result (canonical unit)"),
        ("labs", "unit", "Canonical unit"),
        ("labs", "abnormal_flag", "Low / Normal / High / Unknown"),
        ("vitals", "systolic", "Systolic BP (mmHg) parsed from free text"),
        ("vitals", "diastolic", "Diastolic BP (mmHg) parsed from free text"),
        ("vitals", "temp_c", "Temperature in Celsius"),
        ("vitals", "weight_kg", "Weight in kg"),
        ("vitals", "bmi", "Body mass index (derived)"),
        ("medications", "rxnorm", "RxNorm code"),
        ("claims", "billed_amt", "Billed amount USD"),
        ("claims", "paid_amt", "Paid amount USD"),
        ("claims", "denied", "True if claim was denied"),
    ]
    ws = wb.create_sheet("Data Dictionary")
    ws.append(["Table", "Field", "Description"])
    for row in dd:
        ws.append(row)
    for c in ws[1]:
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 70


def add_readme(wb):
    ws = wb.create_sheet("README", 0)
    ws["A1"] = "Healthcare Data Normalization — Deliverable Workbook"
    ws["A1"].font = Font(bold=True, size=14)
    lines = [
        "",
        "Source: Synthetic EHR-style dataset (no real PHI).",
        "Pipeline: generate_raw_data.py -> profile_data.py -> clean_normalize.py -> export_excel.py",
        "",
        "Normalization summary:",
        "  - Patients deduplicated on MRN (suffix '-A' collapsed).",
        "  - Names trimmed/title-cased; typo '@' repaired to 'a'.",
        "  - Race/Ethnicity standardized; missing -> 'Unknown'.",
        "  - Sex standardized to Male/Female/Other-Unknown.",
        "  - Dates parsed to ISO; future admits removed; discharge<admit -> NaT.",
        "  - ICD-9 codes mapped to ICD-10 via crosswalk; system retained.",
        "  - Labs: mmol/L -> mg/dL (glucose), umol/L -> mg/dL (creatinine);",
        "    abnormal flags derived from reference ranges.",
        "  - Vitals: BP free text parsed to systolic/diastolic; temp F->C;",
        "    weight lb->kg; BMI derived.",
        "  - Claims: denied flag; reimbursement_rate derived.",
        "",
        "Assumptions:",
        "  - Any row with missing DOB keeps DOB=NaT; age remains null.",
        "  - Test patients flagged in raw data are removed.",
        "  - When duplicate patients differ, the row with fewest nulls wins.",
        "",
        "Known limitations:",
        "  - Small synthetic sample; not statistically representative.",
        "  - ICD mapping limited to a curated crosswalk.",
    ]
    for i, l in enumerate(lines, start=2):
        ws[f"A{i}"] = l
    ws.column_dimensions["A"].width = 95


def main():
    with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
        # Placeholder to initialize workbook
        pd.DataFrame({"placeholder": []}).to_excel(writer, sheet_name="__init", index=False)

    # Load and build properly
    wb = load_workbook(OUT)
    del wb["__init"]

    for t in TABLES:
        path = PROCESSED_DIR / f"{t}.csv"
        if not path.exists():
            print(f"[!] Missing {path}")
            continue
        df = pd.read_csv(path)
        ws = wb.create_sheet(t.capitalize())
        write_table(ws, df)

        # Data validation examples
        if t == "patients" and "sex" in df.columns:
            dv = DataValidation(type="list",
                                formula1='"Male,Female,Other/Unknown"',
                                allow_blank=True)
            ws.add_data_validation(dv)
            col_letter = chr(ord("A") + list(df.columns).index("sex"))
            dv.add(f"{col_letter}2:{col_letter}{len(df)+1}")

    add_data_dictionary(wb)
    add_readme(wb)

    # Freeze header row on data sheets
    for t in TABLES:
        name = t.capitalize()
        if name in wb.sheetnames:
            wb[name].freeze_panes = "A2"

    wb.save(OUT)
    print(f"[OK] Excel workbook written to {OUT}")


if __name__ == "__main__":
    main()