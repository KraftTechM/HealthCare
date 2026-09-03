# Pharmacy Medication Inventory & Expiry Analysis System

This Python project generates a synthetic dataset of 1,000 medication inventory records, analyzes expiry risk, produces clinical and managerial charts, and exports a standalone HTML executive dashboard.

## Features

- Synthetic pharmaceutical inventory data with dosage, unit cost, critical status, storage location, and expiry dates.
- 30-day risk identification, including item counts and inventory value at risk.
- Static Seaborn/Matplotlib visualizations and interactive Plotly charts.
- TXT, CSV, Excel (`.xlsx`), and standalone HTML reports.

## Installation and execution

### 1. Prerequisites

Install Python 3.9 or later.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the pipeline

```bash
python src/main.py
```

The pipeline writes its results to `output/`:

- `raw_data/medication_inventory.csv` — generated inventory data
- `plots/` — static visualizations
- `reports/` — text, CSV, and Excel action reports
- `consolidated_report/final_report.html` — interactive executive dashboard

`kaleido` supports PNG treemap export. The visualization module uses Matplotlib's headless `Agg` backend, so it runs without a desktop GUI or Tk.
