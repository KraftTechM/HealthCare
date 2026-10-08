# 🩺💳 Drift Detection for Production ML Models

A lightweight, domain-agnostic drift monitoring layer for tabular machine learning models. It detects when the statistical distribution of production data diverges from the training reference distribution and issues a **retraining recommendation** based on a rolling decision policy.

Designed to run in **Google Colab's default environment** — no virtual environments, no NumPy downgrades, no dependency conflicts.

---

## 📖 Table of Contents

1. [Overview](#-overview)
2. [Why Drift Detection Matters](#-why-drift-detection-matters)
3. [Architecture](#-architecture)
4. [Features](#-features)
5. [Getting Started (Google Colab)](#-getting-started-google-colab)
6. [Project Structure](#-project-structure)
7. [How It Works](#-how-it-works)
8. [Domain Use Cases](#-domain-use-cases)
9. [Understanding the Output](#-understanding-the-output)
10. [Retraining Decision Policy](#-retraining-decision-policy)
11. [Design Decisions](#-design-decisions)
12. [Extending the Project](#-extending-the-project)
13. [Production Deployment](#-production-deployment)
14. [Limitations & Caveats](#-limitations--caveats)
15. [References](#-references)
16. [License](#-license)

---

## 🎯 Overview

This project demonstrates a **production-ready drift monitoring layer** for machine learning pipelines. It compares incoming production data against a reference dataset (typically the training distribution) using statistical hypothesis testing, and emits per-feature drift signals that feed into a retraining decision policy.

The project is fully self-contained and includes:

- A reusable `DriftMonitor` class (domain-agnostic).
- Synthetic data generators for **healthcare lab results** and **fraud detection** — each simulating 30 days of production data with drift injection starting on day 15.
- A daily monitoring loop that produces feature-level drift diagnostics.
- A rolling retraining decision policy.
- Visualization utilities for drift ratio trends and distribution shifts.
- A control-feature sanity check to validate thresholds.

**Goal**: Answer the question *"Should this model be retrained?"* with evidence, not guesswork.

---

## 🚨 Why Drift Detection Matters

Machine learning models silently degrade in production. The data they see drifts away from the data they were trained on — due to:

- **Seasonal changes** (flu season, holiday shopping spikes)
- **Population shifts** (demographic changes, new customer segments)
- **Operational changes** (new lab equipment, new payment processors)
- **Adversarial adaptation** (fraudsters changing tactics)
- **Upstream pipeline changes** (schema drift, new features, missing joins)

Without monitoring, this degradation is invisible until business metrics (revenue, patient outcomes, fraud losses) suffer.

Drift detection is the **leading indicator** that triggers investigation and retraining *before* things break.

### The Three Types of Drift

| Type | What Changes | Detected Here? |
| :--- | :--- | :--- |
| **Data Drift (Covariate Shift)** | `P(X)` changes; `P(Y\|X)` stable | ✅ Yes |
| **Label Drift (Prior Shift)** | `P(Y)` changes; `P(X\|Y)` stable | ⚠️ Partial |
| **Concept Drift** | `P(Y\|X)` itself changes | ❌ No (requires performance monitoring) |

This project focuses on **data drift** — the easiest to monitor because it needs no labels.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              DAILY PRODUCTION INPUTS                     │
│       (healthcare lab results / fraud transactions)      │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: DATA QUALITY (schema, nulls, ranges)           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 2: FEATURE DRIFT DETECTION  ← DriftMonitor        │
│    • KS test on numeric features                         │
│    • Chi-Squared test on categorical features            │
│    • Two-gate decision (p-value + effect size)           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 3: ROLLING DECISION POLICY                        │
│    • Sliding window over recent days                     │
│    • Emits: HEALTHY / MONITOR_CLOSELY / RETRAIN          │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 4: ALERTS & RETRAINING TRIGGER                    │
│    • Slack / Email / PagerDuty                           │
│    • Downstream Airflow DAG or Prefect flow              │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Features

- ✅ **Runs in Google Colab's default environment** — no `venv`, no `numpy` downgrade.
- ✅ **Domain-agnostic** — works for healthcare, finance, retail, IoT, or any tabular model.
- ✅ **Two-gate drift decision** — requires *both* statistical significance and a meaningful effect size, avoiding false positives on large samples.
- ✅ **Feature-level diagnostics** — tells you *which* features drifted, not just that "something changed."
- ✅ **Rolling retraining policy** — reacts to sustained drift over multiple days, not single-day noise.
- ✅ **Control-feature sanity check** — features known *not* to drift act as a validation of thresholds.
- ✅ **Streaming-ready** — the design ports easily to `river` for online detection.
- ✅ **Synthetic data included** — 250 healthcare patients × 30 days, 300 fraud accounts × 30 days.

---

## 🚀 Getting Started (Google Colab)

### Prerequisites

None. The notebook uses only Colab's pre-installed stack:
- `numpy`
- `pandas`
- `scipy`
- `matplotlib`

### Running the Notebook

1. Open [Google Colab](https://colab.research.google.com/).
2. Create a new notebook.
3. **Runtime → Change runtime type → CPU** (GPU is not needed).
4. Copy each cell from this repository into the notebook.
5. **Runtime → Run all**.

Total runtime: **~20–40 seconds** on a standard CPU runtime.

### Cell-by-Cell Execution Order

| Cell | Purpose |
| :--- | :--- |
| **Cell 1** | Imports and environment setup |
| **Cell 2** | Generate synthetic healthcare data (250 patients × 30 days) |
| **Cell 3** | Generate synthetic fraud data (300 accounts × 30 days) |
| **Cell 4** | Define the `DriftMonitor` class |
| **Cell 5** | Run healthcare drift monitoring demo |
| **Cell 6** | Run fraud drift monitoring demo |
| **Cell 7** | Generate visualizations |
| **Cell 8** | Print executive summary |

---

## 📁 Project Structure

```
drift-detection/
│
├── README.md
│
├── notebooks/
│   └── drift_detection_demo.ipynb     # Main Colab notebook
│
├── src/
│   ├── drift_monitor.py               # DriftMonitor class
│   ├── data_generators.py             # Synthetic data generators
│   └── decision_policy.py             # Retraining policy
│
└── examples/
    ├── healthcare_pipeline.py         # Healthcare example
    └── fraud_pipeline.py              # Fraud example
```

If you're using the notebook as a single file, all logic lives in one Colab session.

---

## ⚙️ How It Works

### 1. Data Generation

Two synthetic datasets are generated to simulate realistic production conditions:

**Healthcare Labs** (250 patients × 30 days = 7,500 records):
- **Features**: `glucose_mgdl`, `cholesterol_mgdl`, `hemoglobin_gdl`, `creatinine_mgdl`, `age`, `sex`, `bmi`, `assay_lot`
- **Drift injected from day 15**: glucose +8 mg/dL (new assay lot), creatinine ×1.15 (seasonal), age +5 years (population shift), assay_lot distribution flip
- **Control features**: `cholesterol_mgdl`, `sex` (should NOT drift)

**Fraud Transactions** (300 accounts × 30 days ≈ 30,000 records):
- **Features**: `amount_usd`, `hour_of_day`, `txn_count_24h`, `account_age_days`, `merchant_category`, `country`
- **Drift injected from day 15**: 30% of transactions become fraud-ring behavior (country → BR, higher amounts, higher velocity)
- **Control features**: `hour_of_day`, `account_age_days` (should NOT drift)

### 2. Reference Window

The first **10 days** of data form the reference distribution. Days 11–30 are treated as production and are compared against it day by day.

### 3. Statistical Tests

| Feature Type | Test | Effect Size Metric |
| :--- | :--- | :--- |
| Numeric | Kolmogorov-Smirnov (`ks_2samp`) | KS statistic (0–1) |
| Categorical | Chi-Squared (`chi2_contingency`) | Cramér's V (0–1) |

### 4. Two-Gate Decision

A feature is marked as drifted only if **both** conditions hold:

```python
is_drift = (p_value < 0.01) AND (effect_size > 0.10)
```

This prevents false positives that occur when testing large samples (where tiny differences become statistically significant).

### 5. Rolling Decision Policy

The `DriftMonitor.decision()` method looks at the last N days:

```python
if all(recent_days_drift_ratio >= 0.3):
    return "RETRAIN_RECOMMENDED"
elif any(drift):
    return "MONITOR_CLOSELY"
else:
    return "HEALTHY"
```

---

## 🏥🏦 Domain Use Cases

### Healthcare Lab Results

**Why monitoring is essential:**
- Patient safety — a degraded model can miss critical diagnoses.
- Seasonal patterns (flu, allergy) cause legitimate drift.
- New lab equipment or reagent lots change measurement distributions.
- FDA SaMD guidance requires ongoing validation.

**Special considerations:**
- Use **seasonal reference windows** (compare October to last October).
- Monitor drift **per demographic subgroup** to catch hidden fairness issues.
- Include `assay_lot` / `device_id` as features and monitor within each lot.
- Never auto-retrain without clinician review.

### Fraud Detection

**Why monitoring is essential:**
- Fraudsters actively adapt to evade detection (concept drift by design).
- Extreme class imbalance (0.1–2%) requires careful sampling.
- Delayed labels (30–90 days for chargebacks) mean ground truth is late.
- Financial regulators require documented model risk management.

**Special considerations:**
- Adversaries may try to evade your **drift detector too** — rotate reference windows.
- Feedback loops (blocked transactions never produce labels) — use counterfactual estimation.
- Pair drift signals with business KPIs (fraud rate, chargeback rate).

---

## 📊 Understanding the Output

### Daily Monitoring Table

```
Day  n_drift  drift_ratio  Decision             Drifted features
------------------------------------------------------------------------
11   1        0.14         INSUFFICIENT_HISTORY  assay_lot
12   0        0.00         INSUFFICIENT_HISTORY  —
13   1        0.14         MONITOR_CLOSELY       assay_lot
14   0        0.00         MONITOR_CLOSELY       —
15   2        0.29         MONITOR_CLOSELY       glucose, assay_lot
16   3        0.43         RETRAIN_RECOMMENDED   glucose, creatinine, assay_lot
17   4        0.57         RETRAIN_RECOMMENDED   glucose, creatinine, assay_lot, age
...
30   4        0.57         RETRAIN_RECOMMENDED   glucose, creatinine, assay_lot, age
```

### Per-Feature Breakdown (Day 30)

```
Feature               Test    p-value      Effect    Drift?
-----------------------------------------------------------------
glucose_mgdl          KS      0.000000     0.1820    ⚠️  YES
cholesterol_mgdl      KS      0.452100     0.0310    ✅ NO
hemoglobin_gdl        KS      0.210400     0.0420    ✅ NO
creatinine_mgdl       KS      0.000000     0.1510    ⚠️  YES
age                   KS      0.000100     0.1280    ⚠️  YES
sex                   Chi2    0.624100     0.0180    ✅ NO
assay_lot             Chi2    0.000000     0.6210    ⚠️  YES
```

**Reading this:** 4 of 7 features show both significant p-values AND meaningful effect sizes. Control features (`cholesterol`, `hemoglobin`, `sex`) remain stable — the pipeline is behaving correctly.

### Decision Categories

| Decision | Meaning | Suggested Action |
| :--- | :--- | :--- |
| `HEALTHY` | No drift detected | Continue monitoring |
| `MONITOR_CLOSELY` | Some drift, not sustained | Investigate feature causes |
| `RETRAIN_RECOMMENDED` | Sustained drift above threshold | Trigger retraining pipeline |
| `INSUFFICIENT_HISTORY` | Fewer than N days of history | Wait for more data |

---

## 🔄 Retraining Decision Policy

The policy is intentionally **conservative**. It answers:

> *"Has drift been sustained long enough to justify retraining?"*

### Default Policy

| Condition | Action |
| :--- | :--- |
| 3 consecutive days with drift ratio ≥ 30% | `RETRAIN_RECOMMENDED` |
| Any drift in recent window but < 30% | `MONITOR_CLOSELY` |
| No drift in recent window | `HEALTHY` |

### Recommended Production Policy (Extended)

For production, combine multiple signals:

| Rule | Action |
| :--- | :--- |
| Drift on >30% of features for 3 days | Slack alert to ML team |
| Drift on >50% of features for 7 days AND performance dropped >5% | Auto-trigger retraining |
| Drift detected but performance stable | Log only, no action |
| No drift but performance dropped | Investigate — likely concept drift |
| Data quality check fails | Halt pipeline, do NOT retrain |

**Rule of thumb:** never retrain on drift alone. Retrain on **drift + performance degradation**.

---

## 🎨 Design Decisions

### Why KS and Chi-Squared?

- **Non-parametric** — no assumptions about the distribution shape.
- **Widely understood** — every data scientist knows these tests.
- **Fast** — O(n log n), handles millions of rows in milliseconds.
- **Feature-level** — produces per-feature p-values, enabling targeted investigation.

### Why the Two-Gate Decision?

p-values alone are misleading for large samples. With 100,000 records, a 0.1% shift in means can produce p < 0.001 — but may be practically irrelevant.

The **effect size gate** ensures we only flag drift that is *both* statistically detectable *and* operationally meaningful.

### Why Rolling Windows?

Single-day drift signals are noisy. A model retrained on one anomalous day would be worse than the original. Requiring **3 consecutive days** of drift filters out short-lived anomalies (data pipeline hiccups, one-off events).

### Why Control Features?

The synthetic data includes features that are **deliberately not drifted** (e.g., `cholesterol_mgdl`, `sex`, `hour_of_day`). These act as a **sanity check**:
- If control features show drift → thresholds are too loose, or the pipeline is broken.
- If control features stay stable → the detector is behaving correctly.

### Why No Virtual Environment?

The original attempt used `alibi-detect`, which requires `numpy<2.0` — incompatible with Colab's current stack. Rather than fight dependencies, this project uses only Colab's pre-installed libraries:
- `scipy.stats.ks_2samp` — same KS test `alibi-detect` uses internally.
- `scipy.stats.chi2_contingency` — same Chi-Squared test.
- `river` (optional) — for streaming drift detection, compatible with NumPy 2.

**Result**: `Runtime → Run all` just works.

---

## 🛠️ Extending the Project

### Add Prediction Drift Monitoring

Monitor the distribution of model **outputs** (scores, classes), not just inputs:

```python
class PredictionDriftMonitor(DriftMonitor):
    def check_predictions(self, ref_preds, cur_preds, date=None):
        # Compare distribution of predicted probabilities or classes
        return self.check(pd.DataFrame({"score": cur_preds}), date)
```

### Add Label-Free Performance Estimation

Use **NannyML CBPE** (Confidence-Based Performance Estimation) to estimate accuracy without labels:

```python
!pip install nannyml
import nannyml as nml

estimator = nml.CBPE(
    problem_type='classification_binary',
    y_pred_proba='predicted_score',
    y_pred='predicted_class',
    metrics=['roc_auc'],
    chunk_size=500,
)
estimator.fit(reference_df)
results = estimator.estimate(production_df)
```

### Add Fairness Monitoring

Run drift tests **per subgroup** to detect hidden fairness issues:

```python
for group in ["M", "F"]:
    subgroup_monitor = DriftMonitor(
        reference_df=hc_ref[hc_ref["sex"] == group],
        numeric_features=[...],
        categorical_features=[...],
    )
    subgroup_monitor.check(production_df[production_df["sex"] == group])
```

### Port to Streaming (River)

For real-time detection, use `river`:

```python
!pip install river
from river.drift import ADWIN, PageHinkley

adwin = ADWIN(delta=0.002)
for value in stream:
    adwin.update(value)
    if adwin.drift_detected:
        print("Drift detected!")
```

### Integration with Airflow

```python
# dag_drift_check.py
from airflow import DAG
from airflow.operators.python import PythonOperator

def run_daily_drift_check():
    from drift_monitor import DriftMonitor
    # ... load today's data, run check, push metrics

with DAG("daily_drift_check", schedule="0 2 * * *") as dag:
    check = PythonOperator(task_id="check_drift", python_callable=run_daily_drift_check)
```

---

## 🏭 Production Deployment

### Recommended Stack

| Layer | Tool |
| :--- | :--- |
| **Scheduling** | Airflow, Prefect, or Dagster |
| **Metrics export** | Prometheus, Datadog, or CloudWatch |
| **Alerting** | Slack, PagerDuty, or Opsgenie |
| **Dashboards** | Grafana, Evidently AI, or WhyLabs |
| **Storage** | Postgres, BigQuery, or S3 |
| **Managed platforms** | Evidently Cloud, Arize, Fiddler, WhyLabs |

### Daily Workflow

```
2:00 AM  → Fetch yesterday's production features
2:05 AM  → Sample (5,000 rows sufficient for drift tests)
2:06 AM  → Run DriftMonitor.check()
2:07 AM  → Push per-feature drift metrics to Prometheus
2:08 AM  → Evaluate retraining decision policy
2:09 AM  → Alert if RETRAIN_RECOMMENDED
2:10 AM  → Log to audit trail (regulatory requirement)
```

### Cost Estimation

- **Compute**: negligible — statistical tests are lightweight.
- **Storage**: <1 GB/year for daily summaries at feature granularity.
- **Cloud function**: runs comfortably on 512 MB RAM.

---

## ⚠️ Limitations & Caveats

1. **Detects data drift only** — not concept drift. Pair with performance monitoring when labels arrive.

2. **No causal interpretation** — a drift signal does not tell you *why* the data changed. Investigate root causes manually.

3. **Reference window staleness** — comparing to a 2-year-old training set creates false positives. Use a rolling reference (last 30–90 days) in production.

4. **Alert fatigue** — poorly tuned thresholds get ignored. Start conservative (p<0.01, effect>0.10) and tighten based on observed false-positive rates.

5. **Batch effects vs. real drift** — a new batch of data from a different source may look like drift but reflect measurement differences. Include batch/device IDs as features.

6. **Subgroup blindness** — aggregate drift can hide subgroup drift. Run per-segment tests for fairness-critical applications.

7. **Delayed labels** — this project doesn't estimate accuracy without labels. For that, use **NannyML CBPE** or **DLE**.

---

## 📚 References

### Drift Detection Methods

- Gama, J., et al. (2014). *A survey on concept drift adaptation.* ACM Computing Surveys.
- Lu, J., et al. (2018). *Learning under concept drift: A review.* IEEE TKDE.
- Rabanser, S., et al. (2019). *Failing loudly: An empirical study of methods for detecting dataset shift.* NeurIPS.

### Libraries & Tools

- **Evidently AI** — https://github.com/evidentlyai/evidently
- **NannyML** — https://github.com/NannyML/nannyml
- **River** — https://github.com/online-ml/river
- **Alibi-Detect** — https://github.com/SeldonIO/alibi-detect
- **PyOD** — https://github.com/yzhao062/pyod
- **WhyLabs** — https://whylabs.ai

### Regulatory Frameworks

- **EU AI Act** — Article 15 (accuracy, robustness, cybersecurity), Article 72 (post-market monitoring)
- **FDA SaMD** — Predetermined Change Control Plans (PCCP)
- **SR 11-7** (US Federal Reserve) — Model Risk Management guidance

### Further Reading

- *Designing Machine Learning Systems* — Chip Huyen (O'Reilly, 2022)
- *Machine Learning Design Patterns* — Lakshmanan et al. (O'Reilly, 2020)
- *Reliable Machine Learning* — Chen et al. (O'Reilly, 2022)

---

## 📄 License

MIT License. See `LICENSE` for details.

---

## 🙏 Acknowledgments

- The synthetic data generators are inspired by real-world healthcare and fraud monitoring patterns.
- The two-gate decision policy (p-value + effect size) follows best practices from the statistical testing literature.
- The rolling retraining policy reflects common MLOps production patterns from industry case studies.

---
