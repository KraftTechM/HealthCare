"""
Advanced CEO dashboard views:
  11. Trend-adjusted equity gaps
  12. Revenue cycle waterfall
  13. Readmission cohort heatmap (DRG x Month)
  14. Facility x Month operations heatmap
Outputs to reports/ceo_dashboard/ (same folder as base dashboard).
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


# -- Load + enrich (same pattern as base script) --------------------------
def load_all():
    t = {}
    for name in ["dim_patient", "dim_date", "dim_facility", "dim_encounter_type",
                 "fact_encounter", "fact_claim"]:
        t[name] = pd.read_csv(STAR_DIR / f"{name}.csv")
    t["dim_date"]["date"] = pd.to_datetime(t["dim_date"]["date"])
    return t


def enrich(t):
    enc = (t["fact_encounter"]
           .merge(t["dim_date"][["date_key", "date", "year", "year_month", "quarter"]],
                  left_on="admit_date_key", right_on="date_key", how="left")
           .merge(t["dim_facility"], on="facility_key", how="left")
           .merge(t["dim_encounter_type"], on="encounter_type_key", how="left")
           .merge(t["dim_patient"][["patient_key", "race", "ethnicity",
                                    "age_band", "sex", "payer"]],
                  on="patient_key", how="left"))

    clm = (t["fact_claim"]
           .merge(t["dim_date"][["date_key", "date", "year", "year_month"]],
                  on="date_key", how="left")
           .merge(t["dim_patient"][["patient_key", "race", "age_band"]],
                  on="patient_key", how="left"))
    return enc, clm


def save(fig, name):
    path = OUT_DIR / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {name}")


# -------------------------------------------------------------------------
# 11. Trend-adjusted equity gaps
# -------------------------------------------------------------------------
def chart_equity_trend(enc):
    """
    For each year, compute:
      - Avg LOS per race
      - Disparity gap = max(race LOS) - min(race LOS)
      - Also show racial group values as a small-multiple line chart
    """
    df = enc.dropna(subset=["race", "los_days", "year"])
    df = df[(df["race"] != "Unknown") & (df["los_days"] > 0)]

    by_year_race = (df.groupby(["year", "race"])["los_days"]
                    .mean().reset_index())

    # Overall gap per year
    gap = (by_year_race.groupby("year")["los_days"]
           .agg(["min", "max"]).reset_index())
    gap["disparity_gap"] = gap["max"] - gap["min"]

    # Overall mean LOS per year (for reference)
    overall = df.groupby("year")["los_days"].mean().reset_index(name="overall_los")

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Panel 1: LOS by race over time
    sns.lineplot(data=by_year_race, x="year", y="los_days",
                 hue="race", marker="o", ax=axes[0], palette="Set2")
    axes[0].set_title("Avg Length of Stay by Race Over Time")
    axes[0].set_ylabel("Avg LOS (days)")
    axes[0].set_xlabel("Year")
    axes[0].legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)

    # Panel 2: Disparity gap over time
    axes[1].plot(gap["year"], gap["disparity_gap"],
                 marker="o", color="darkred", linewidth=2.5, label="Gap (max − min)")
    axes[1].fill_between(gap["year"], gap["disparity_gap"], alpha=0.15, color="darkred")
    axes[1].axhline(gap["disparity_gap"].mean(), linestyle="--",
                    color="gray", linewidth=1.2,
                    label=f"Mean gap = {gap['disparity_gap'].mean():.2f}d")
    axes[1].set_title("LOS Disparity Gap by Year  (lower = more equitable)")
    axes[1].set_ylabel("Gap (days)")
    axes[1].set_xlabel("Year")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Annotate trend
    if len(gap) >= 2:
        first, last = gap["disparity_gap"].iloc[0], gap["disparity_gap"].iloc[-1]
        delta = last - first
        direction = "narrowing" if delta < 0 else "widening"
        axes[1].text(0.5, 0.02,
                     f"Gap {direction} by {abs(delta):.2f}d  ({first:.2f} → {last:.2f})",
                     transform=axes[1].transAxes, ha="center", fontsize=10,
                     color="darkgreen" if delta < 0 else "darkred")

    fig.suptitle("Equity Trend Analysis — Are Disparities Improving?",
                 fontsize=15, fontweight="bold", y=1.02)
    save(fig, "11_equity_trend.png")


# -------------------------------------------------------------------------
# 12. Revenue cycle waterfall
# -------------------------------------------------------------------------
def chart_revenue_waterfall(clm):
    """
    Billed -> (Denials) -> (Contractual) -> Net Collected
    Contractual is derived: Billed - Denied - Paid
    """
    billed = clm["billed_amt"].sum()
    denied_billed = clm.loc[clm["denied"], "billed_amt"].sum()
    paid = clm["paid_amt"].sum()
    contractual = billed - denied_billed - paid

    steps = [
        ("Gross Billed",     billed,      "total"),
        ("Denied",          -denied_billed, "change"),
        ("Contractual",     -contractual,   "change"),
        ("Net Collected",    paid,        "total"),
    ]

    labels = [s[0] for s in steps]
    values = [s[1] for s in steps]
    types  = [s[2] for s in steps]

    fig, ax = plt.subplots(figsize=(11, 6))
    running = 0.0
    colors = {"total": "#1F4E78", "change": "#C00000", "positive": "#2E7D32"}

    for i, (label, val, typ) in enumerate(steps):
        if typ == "total":
            ax.bar(i, val / 1e6, color=colors["total"], width=0.6)
            running = val
            ax.text(i, val / 1e6 + billed / 1e6 * 0.02,
                    f"${val/1e6:.1f}M", ha="center", fontweight="bold", fontsize=11)
        else:
            bottom = running + val
            ax.bar(i, abs(val) / 1e6, bottom=bottom / 1e6,
                   color=colors["change"], width=0.6)
            ax.text(i, (bottom + abs(val) / 2) / 1e6,
                    f"−${abs(val)/1e6:.1f}M", ha="center", va="center",
                    color="white", fontweight="bold", fontsize=11)
            # connector line
            ax.plot([i - 0.3, i + 0.3], [bottom / 1e6, bottom / 1e6],
                    color="gray", linewidth=0.8, linestyle="--")
            running = bottom

    # Final connector from last change to Net Collected top
    ax.plot([2 + 0.3, 3 - 0.3], [paid / 1e6, paid / 1e6],
            color="gray", linewidth=0.8, linestyle="--")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("USD (millions)")
    ax.set_title("Revenue Cycle Waterfall — Billed to Collected")

    # Summary stats box
    collection_rate = paid / billed
    denial_rate = denied_billed / billed
    contractual_rate = contractual / billed
    summary = (f"Net Collection Rate: {collection_rate:.1%}\n"
               f"Denial Rate (of billed): {denial_rate:.1%}\n"
               f"Contractual Adjustment: {contractual_rate:.1%}")
    ax.text(0.98, 0.97, summary, transform=ax.transAxes,
            ha="right", va="top", fontsize=11,
            bbox=dict(boxstyle="round", facecolor="#F2F2F2",
                      edgecolor="#1F4E78", linewidth=1.5))
    save(fig, "12_revenue_waterfall.png")


# -------------------------------------------------------------------------
# 13. Readmission cohort heatmap (DRG x Month)
# -------------------------------------------------------------------------
def chart_readmission_heatmap(enc):
    """
    Cohort heatmap: for each encounter (as a cohort start), flag whether the
    same patient returned within 30 days. Aggregate by DRG x Year-Month.
    Only top DRGs shown.
    """
    df = enc.dropna(subset=["patient_key", "date", "drg"]).copy()
    df = df.sort_values(["patient_key", "date"])

    df["next_admit"] = df.groupby("patient_key")["date"].shift(-1)
    df["days_to_next"] = (df["next_admit"] - df["date"]).dt.days
    df["readmitted_30d"] = ((df["days_to_next"] > 0) &
                            (df["days_to_next"] <= 30))

    # Top 10 DRGs by volume
    top_drg = df["drg"].value_counts().head(10).index
    sub = df[df["drg"].isin(top_drg)].copy()

    # Pivot: DRG rows, year_month cols, mean(readmitted_30d)
    pivot = (sub.groupby(["drg", "year_month"])["readmitted_30d"]
             .mean().unstack(fill_value=np.nan))

    # Sort months chronologically
    pivot = pivot.reindex(sorted(pivot.columns), axis=1)
    # Sort DRGs by overall rate (descending)
    pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]

    if pivot.empty:
        print("  [!] No data for readmission heatmap")
        return

    fig, ax = plt.subplots(figsize=(max(14, len(pivot.columns) * 0.4),
                                    max(6, len(pivot) * 0.5)))
    sns.heatmap(pivot, cmap="YlOrRd", annot=False, fmt=".0%",
                cbar_kws={"label": "30-day Readmission Rate"},
                linewidths=0.3, linecolor="white", ax=ax)
    ax.set_title("Readmission Rate by DRG × Month (Cohort Heatmap)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Admission Month")
    ax.set_ylabel("DRG")
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    ax.tick_params(axis="y", rotation=0, labelsize=9)
    save(fig, "13_readmission_heatmap.png")


# -------------------------------------------------------------------------
# 14. Facility x Month operations heatmap
# -------------------------------------------------------------------------
def chart_facility_heatmap(enc):
    """
    Volume + severity heatmap by facility x month.
    Color = Avg LOS (proxy for case-mix complexity / operational strain).
    Annotation = encounter count.
    """
    df = enc.dropna(subset=["facility", "year_month", "los_days"]).copy()
    df = df[df["los_days"] > 0]

    pivot_los = df.pivot_table(index="facility", columns="year_month",
                               values="los_days", aggfunc="mean")
    pivot_count = df.pivot_table(index="facility", columns="year_month",
                                 values="encounter_id", aggfunc="count")

    pivot_los = pivot_los.reindex(sorted(pivot_los.columns), axis=1)
    pivot_count = pivot_count.reindex_like(pivot_los)

    fig, ax = plt.subplots(figsize=(max(14, len(pivot_los.columns) * 0.4), 5))
    sns.heatmap(pivot_los, cmap="RdYlGn_r", annot=pivot_count.astype("Int64"),
                fmt="", linewidths=0.3, linecolor="white",
                cbar_kws={"label": "Avg LOS (days)"}, ax=ax)
    ax.set_title("Operational Load — Avg LOS by Facility × Month\n"
                 "(cell number = encounter count)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Facility")
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    ax.tick_params(axis="y", rotation=0, labelsize=9)
    save(fig, "14_facility_operations_heatmap.png")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------
def main():
    print("Loading star schema...")
    t = load_all()

    print("Enriching...")
    enc, clm = enrich(t)

    print("Generating advanced CEO charts...")
    chart_equity_trend(enc)
    chart_revenue_waterfall(clm)
    chart_readmission_heatmap(enc)
    chart_facility_heatmap(enc)

    print(f"\nAll advanced charts saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()