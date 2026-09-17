
## Normalization rules applied

| Issue | Rule |
|---|---|
| Duplicate MRNs | Collapse `-A` suffix; keep row with fewest nulls |
| Test patients | Removed (flag from raw) |
| Names | Trim, title-case, repair `@`→`a` typos |
| Sex | Standardize M / F / Male / Female → Male / Female / Other |
| Race / Ethnicity | Map to standard categories; missing → `Unknown` |
| ICD-9 codes | Auto-map to ICD-10 via curated crosswalk; keep original system |
| Lab units | mmol/L → mg/dL (glucose); µmol/L → mg/dL (creatinine) |
| Lab abnormal flag | Derived from LOINC reference range |
| BP free text | Regex-parsed to systolic / diastolic; implausible values dropped |
| Temperature | F → C |
| Weight | lb → kg |
| BMI | Derived from weight + height |
| Future admits | Removed (data entry errors) |
| Discharge < admit | Discharge reset to null |
| Claims | Denied flag + reimbursement_rate derived |
| Dates | ISO-parsed; surrogate `YYYYMMDD` integer keys |

## Deliverables

1. **Cleaned & normalized dataset** — `data/processed/*.csv` + `reports/healthcare_normalized.xlsx`
2. **Star schema** — `data/star_schema/` (10 dims, 6 facts, validated 25/25)
3. **Power BI model** — `powerbi/HealthCareAnalytics.bim` + `measures.dax`
4. **Build guide** — `powerbi_build_guide.md`
5. **Documentation** — `reports/data_quality_report.txt` + README

## KPIs implemented

- **Clinical quality:** BP control rate, HbA1c control rate, abnormal lab rate, obesity rate
- **Utilization:** total encounters, LOS (avg + median), encounters per patient, ED volume
- **Readmissions:** 30-day readmission rate
- **Financial:** billed, paid, net collection rate, denial rate, avg billed/paid per encounter
- **Equity:** LOS gap, encounters per 1000, denial rate by payer
- **Time intelligence:** YoY %, MoM %, rolling 90-day encounters

## How to run

```bash
# 1. Environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
python -m pip install -r requirements.txt

# 2. Pipeline
python src/generate_raw_data.py
python src/profile_data.py
python src/clean_normalize.py
python src/export_excel.py
python src/build_star_schema.py
python src/validate_star_schema.py

# 3. Optional cleanup
python src/fix_date_dim.py
python src/fix_future_claims.py

# 4. Power BI
#    - Open Power BI Desktop, blank report
#    - External Tools → Tabular Editor
#    - File → Open → From File… → powerbi/HealthCareAnalytics.bim
#    - Save back to Power BI; follow powerbi_build_guide.md