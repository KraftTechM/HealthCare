"""
CEO Decision Dashboard
Generates executive-level charts + KPI summary table from the star schema.
Outputs:
  reports/ceo_dashboard/*.png
  reports/ceo_dashboard/executive_kpis.csv
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from pathlib import Path

from config import PROCESSED_DIR, REPORTS_DIR

STAR_DIR = PROCESSED_DIR.parent / "star_schema"
OUT_DIR = REPORTS_DIR / "ceo_dashboard"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -- Style ----------------------------------------------------------------
sns.set_theme(style="whitegrid", context="talk")
PALETTE = sns.color_palette("Set2")
plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 150,
    "figure.facecolor": "white",
    "axes.titleweight": "bold",
    "axes.titlesize": 14,
    "axes.labelsize": 11,
})

# -- Load -----------------------------------------------------------------
def load_all():
    t = {}
    for name in ["dim_patient", "dim_date", "dim_facility", "dim_department",
                 "dim_provider", "dim_encounter_type", "dim_diagnosis",
                 "dim_lab", "dim_medication", "dim_payer",
                 "fact_encounter", "fact_diagnosis", "fact_lab",
                 "fact_vitals", "fact_medication", "fact_claim"]:
        t[name] = pd.read_csv(STAR_DIR / f"{name}.csv")
    t["dim_date"]["date"] = pd.to_datetime(t["dim_date"]["date"])
    return t


def enrich(t):
    """Join facts to dims for flat analysis."""
    enc = (t["fact_encounter"]
           .merge(t["dim_date"][["date_key", "date", "year", "year_month",
                                 "quarter", "month_name"]],
                  left_on="admit_date_key", right_on="date_key", how="left")
           .merge(t["dim_facility"], on="facility_key", how="left")
           .merge(t["dim_department"], on="department_key", how="left")
           .merge(t["dim_encounter_type"], on="encounter_type_key", how="left")
           .merge(t["dim_patient"][["patient_key", "race", "ethnicity",
                                    "age_band", "sex", "payer"]],
                  on="patient_key", how="left"))
    clm = (t["fact_claim"]
           .merge(t["dim_date"][["date_key", "date", "year", "year_month"]],
                  on="date_key", how="left")
           .merge(t["dim_payer"], on="payer_key", how="left")
           .merge(t["dim_patient"][["patient_key", "race", "ethnicity",
                                    "age_band", "sex"]],
                  on="patient_key", how="left"))
    lab = (t["fact_lab"]
           .merge(t["dim_lab"], on="lab_key", how="left")
           .merge(t["dim_date"][["date_key", "year_month", "year"]],
                  on="date_key", how="left"))
    vit = (t["fact_vitals"]
           .merge(t["dim_date"][["date_key", "year_month"]],
                  on="date_key", how="left")
           .merge(t["dim_patient"][["patient_key", "race", "age_band"]],
                  on="patient_key", how="left"))
    dx = (t["fact_diagnosis"]
          .merge(t["dim_diagnosis"], on="diagnosis_key", how="left"))
    return enc, clm, lab, vit, dx


# -- KPI computations -----------------------------------------------------
def compute_kpis(enc, clm, lab, vit):
    kpi = {}
    kpi["Total Encounters"] = len(enc)
    kpi["Unique Patients"] = enc["patient_key"].nunique()
    kpi["Total Billed ($)"] = round(clm["billed_amt"].sum(), 2)
    kpi["Total Paid ($)"] = round(clm["paid_amt"].sum(), 2)
    kpi["Net Collection Rate"] = round(clm["paid_amt"].sum() / clm["billed_amt"].sum(), 4)
    kpi["Denial Rate"] = round(clm["denied"].mean(), 4)
    kpi["Avg Length of Stay (d)"] = round(
        enc.loc[enc["los_days"] > 0, "los_days"].mean(), 2)
    kpi["Median Length of Stay (d)"] = round(
        enc.loc[enc["los_days"] > 0, "los_days"].median(), 2)
    kpi["Encounters per Patient"] = round(len(enc) / enc["patient_key"].nunique(), 2)
    kpi["Avg Billed / Encounter ($)"] = round(
        clm["billed_amt"].sum() / len(enc), 2)

    # Clinical
    bp_ok = vit.dropna(subset=["systolic", "diastolic"]).groupby("encounter_id").agg(
        sys=("systolic", "max"), dia=("diastolic", "max"))
    kpi["BP Control Rate"] = round(
        ((bp_ok["sys"] < 140) & (bp_ok["dia"] < 90)).mean(), 4)

    kpi["Abnormal Lab Rate"] = round(
        lab["abnormal_flag"].isin(["High", "Low"]).mean(), 4)

    bmi = vit.dropna(subset=["bmi"]).groupby("patient_key")["bmi"].max()
    kpi["Obesity Rate (BMI>=30)"] = round((bmi >= 30).mean(), 4)

    # Readmission proxy: same patient_key, second admit within 30d
    enc_s = enc[["patient_key", "date"]].dropna().sort_values(["patient_key", "date"])
    enc_s["prev"] = enc_s.groupby("patient_key")["date"].shift(1)
    enc_s["gap_days"] = (enc_s["date"] - enc_s["prev"]).dt.days
    kpi["30-day Readmission Rate"] = round(
        ((enc_s["gap_days"] >= 0) & (enc_s["gap_days"] <= 30)).mean(), 4)
    return kpi


# -- Charts ---------------------------------------------------------------
def save(fig, name):
    path = OUT_DIR / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {name}")


def chart_financial_trend(clm):
    monthly = clm.groupby("year_month").agg(
        billed=("billed_amt", "sum"),
        paid=("paid_amt", "sum")).reset_index()
    monthly["collection_rate"] = monthly["paid"] / monthly["billed"]

    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.bar(monthly["year_month"], monthly["billed"] / 1e6,
            label="Billed ($M)", color=PALETTE[0], alpha=0.85)
    ax1.bar(monthly["year_month"], monthly["paid"] / 1e6,
            label="Paid ($M)", color=PALETTE[1], alpha=0.9)
    ax1.set_ylabel("USD (millions)")
    ax1.set_xlabel("Month")
    ax1.set_title("Financial Performance — Monthly Billed vs Paid")
    ax1.tick_params(axis="x", rotation=60, labelsize=8)
    ax2 = ax1.twinx()
    ax2.plot(monthly["year_month"], monthly["collection_rate"],
             color="darkred", marker="o", linewidth=2, label="Collection Rate")
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax2.set_ylabel("Collection Rate", color="darkred")
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    save(fig, "01_financial_trend.png")


def chart_denial_by_payer(clm):
    d = clm.groupby("payer").agg(
        total=("claim_id", "count"),
        denied=("denied", "sum")).reset_index()
    d["rate"] = d["denied"] / d["total"]
    d = d.sort_values("rate", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(d["payer"], d["rate"], color=PALETTE[3])
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title("Denial Rate by Payer")
    ax.set_xlabel("Denial Rate")
    for b, v in zip(bars, d["rate"]):
        ax.text(b.get_width() + 0.002, b.get_y() + b.get_height() / 2,
                f"{v:.1%}", va="center", fontsize=10)
    save(fig, "02_denial_by_payer.png")


def chart_encounters_by_dept(enc):
    d = enc.groupby("department").agg(
        encounters=("encounter_id", "count"),
        avg_los=("los_days", "mean")).reset_index()
    d = d.sort_values("encounters", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(d["department"], d["encounters"], color=PALETTE[2])
    ax.set_title("Encounter Volume & Avg LOS by Department")
    ax.set_xlabel("Encounters")
    for b, v, l in zip(bars, d["encounters"], d["avg_los"]):
        ax.text(b.get_width() + 5, b.get_y() + b.get_height() / 2,
                f"{int(v)}  (LOS {l:.1f}d)", va="center", fontsize=9)
    save(fig, "03_encounters_by_department.png")


def chart_facility_comparison(enc):
    d = enc.groupby("facility").agg(
        encounters=("encounter_id", "count"),
        avg_los=("los_days", "mean")).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    sns.barplot(data=d, x="encounters", y="facility", ax=axes[0], palette="Blues_d")
    axes[0].set_title("Encounter Volume by Facility")
    sns.barplot(data=d, x="avg_los", y="facility", ax=axes[1], palette="Reds_d")
    axes[1].set_title("Avg Length of Stay by Facility")
    axes[1].set_xlabel("Days")
    save(fig, "04_facility_comparison.png")


def chart_encounter_mix(enc):
    d = enc["encounter_type"].value_counts()
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(d.values, labels=d.index, autopct="%1.1f%%",
           colors=PALETTE, startangle=90, wedgeprops={"edgecolor": "white"})
    ax.set_title("Encounter Mix")
    save(fig, "05_encounter_mix.png")


def chart_quality(lab, vit):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # BP control by department-level proxy — use race for equity view
    lab_rate = lab.groupby("result_name")["abnormal_flag"].apply(
        lambda s: s.isin(["High", "Low"]).mean()).sort_values(ascending=True)

    sns.barplot(x=lab_rate.values, y=lab_rate.index, ax=axes[0], palette="Oranges_r")
    axes[0].xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    axes[0].set_title("Abnormal Rate by Lab Test")
    axes[0].set_xlabel("Abnormal Rate")

    bp = vit.dropna(subset=["systolic", "diastolic"]).copy()
    bp["bp_class"] = np.where(
        (bp["systolic"] < 120) & (bp["diastolic"] < 80), "Normal",
        np.where((bp["systolic"] < 140) & (bp["diastolic"] < 90), "Elevated", "High"))
    counts = bp["bp_class"].value_counts().reindex(["Normal", "Elevated", "High"]).fillna(0)
    axes[1].pie(counts.values, labels=counts.index, autopct="%1.1f%%",
                colors=["#66c2a5", "#fc8d62", "#e41a1c"], startangle=90,
                wedgeprops={"edgecolor": "white"})
    axes[1].set_title("BP Classification Distribution")
    save(fig, "06_clinical_quality.png")


def chart_equity(enc, clm):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    d1 = enc.groupby("race")["los_days"].mean().sort_values(ascending=True)
    sns.barplot(x=d1.values, y=d1.index, ax=axes[0], palette="Purples_r")
    axes[0].set_title("Avg LOS by Race")
    axes[0].set_xlabel("Days")

    d2 = enc.groupby("age_band")["encounter_id"].count().sort_index()
    sns.barplot(x=d2.index.astype(str), y=d2.values, ax=axes[1], palette="Greens_r")
    axes[1].set_title("Encounter Volume by Age Band")
    axes[1].set_ylabel("Encounters")

    d3 = clm.groupby("race")["denied"].mean().sort_values(ascending=True)
    sns.barplot(x=d3.values, y=d3.index, ax=axes[2], palette="Reds_r")
    axes[2].xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    axes[2].set_title("Denial Rate by Race")
    axes[2].set_xlabel("Denial Rate")
    save(fig, "07_equity.png")


def chart_payer_mix(clm):
    d = clm.groupby("payer")["billed_amt"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(x=d.values / 1e6, y=d.index, ax=ax, palette="Set3")
    ax.set_title("Revenue by Payer ($M)")
    ax.set_xlabel("Billed ($M)")
    save(fig, "08_payer_mix.png")


def chart_volume_trend(enc):
    m = enc.groupby("year_month").size().reset_index(name="encounters")
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(m["year_month"], m["encounters"], marker="o",
            linewidth=2, color=PALETTE[0])
    ax.fill_between(m["year_month"], m["encounters"], alpha=0.2, color=PALETTE[0])
    ax.set_title("Monthly Encounter Volume Trend")
    ax.set_ylabel("Encounters")
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    save(fig, "09_volume_trend.png")


def chart_top_diagnoses(dx):
    d = dx["dx_desc"].value_counts().head(10).sort_values()
    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.barh(d.index, d.values, color=PALETTE[4])
    ax.set_title("Top 10 Diagnoses by Encounter Count")
    ax.set_xlabel("Diagnoses")
    for b, v in zip(bars, d.values):
        ax.text(b.get_width() + 2, b.get_y() + b.get_height() / 2,
                str(v), va="center", fontsize=9)
    save(fig, "10_top_diagnoses.png")


def executive_summary_table(kpi):
    df = pd.DataFrame(list(kpi.items()), columns=["KPI", "Value"])
    df.to_csv(OUT_DIR / "executive_kpis.csv", index=False)

    # Also render as a chart-like table image
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.axis("off")
    ax.set_title("Executive KPI Summary", fontsize=16, fontweight="bold", pad=20)
    table = ax.table(cellText=df.values, colLabels=df.columns,
                     cellLoc="left", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.6)
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#1F4E78")
            cell.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#F2F2F2")
    save(fig, "00_executive_kpis.png")


# -- Main -----------------------------------------------------------------
def main():
    print("Loading star schema...")
    t = load_all()

    print("Enriching...")
    enc, clm, lab, vit, dx = enrich(t)

    print("Computing KPIs...")
    kpi = compute_kpis(enc, clm, lab, vit)
    for k, v in kpi.items():
        print(f"  {k:<32} {v}")
    executive_summary_table(kpi)

    print("\nGenerating CEO charts...")
    chart_financial_trend(clm)
    chart_denial_by_payer(clm)
    chart_encounters_by_dept(enc)
    chart_facility_comparison(enc)
    chart_encounter_mix(enc)
    chart_quality(lab, vit)
    chart_equity(enc, clm)
    chart_payer_mix(clm)
    chart_volume_trend(enc)
    chart_top_diagnoses(dx)

    print(f"\nAll charts saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()