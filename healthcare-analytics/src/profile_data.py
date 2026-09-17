"""
Data quality profiling on the raw healthcare dataset.
Writes a text report to reports/data_quality_report.txt
"""
import pandas as pd
from config import RAW_DIR, REPORTS_DIR

TABLES = ["patients", "encounters", "diagnoses", "labs",
          "vitals", "medications", "claims"]


def profile_table(name: str) -> str:
    path = RAW_DIR / f"{name}_raw.csv"
    df = pd.read_csv(path)
    lines = []
    lines.append(f"\n{'='*70}\nTABLE: {name.upper()}  ({len(df)} rows, {df.shape[1]} cols)\n{'='*70}")

    # Missing values
    miss = df.isna().sum().sort_values(ascending=False)
    miss_pct = (miss / len(df) * 100).round(2)
    lines.append("\n-- Missing values --")
    for col, m in miss.items():
        lines.append(f"  {col:<25} {m:>6}  ({miss_pct[col]:>5}%)")

    # Duplicates
    dup_rows = df.duplicated().sum()
    lines.append(f"\n-- Exact duplicate rows: {dup_rows}")

    if "mrn" in df.columns:
        dup_mrn = df["mrn"].duplicated().sum()
        lines.append(f"-- Duplicate MRNs: {dup_mrn}")

    # Numeric outliers (z-score > 3)
    num = df.select_dtypes(include="number")
    if not num.empty:
        z = (num - num.mean()) / num.std(ddof=0)
        outliers = (z.abs() > 3).sum()
        lines.append("\n-- Numeric outliers (|z| > 3) --")
        for col, c in outliers.items():
            if c:
                lines.append(f"  {col:<25} {c}")

    return "\n".join(lines)


def main():
    report = ["HEALTHCARE DATA QUALITY REPORT",
              f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}",
              "=" * 70]
    for t in TABLES:
        try:
            report.append(profile_table(t))
        except FileNotFoundError:
            report.append(f"\n[!] Missing table: {t}")

    out = REPORTS_DIR / "data_quality_report.txt"
    out.write_text("\n".join(report))
    print(f"Report written to {out}")
    print("\n".join(report))


if __name__ == "__main__":
    main()