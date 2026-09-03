"""Module responsible for exporting reports (TXT, CSV, XLSX, and HTML Dashboard)."""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class ReportGenerator:
    """Generates all requested summary documents and interactive dashboards."""

    def __init__(self, full_df: pd.DataFrame, exp_df: pd.DataFrame, output_dir: str):
        self.full_df = full_df
        self.exp_df = exp_df
        self.output_dir = output_dir
        self.reports_dir = os.path.join(output_dir, "reports")
        self.html_dir = os.path.join(output_dir, "consolidated_report")
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.html_dir, exist_ok=True)

    def export_text_summaries(self, full_summary: dict, exp_summary: dict):
        """Write plain text summary files."""
        # Full Dataset Summary
        with open(os.path.join(self.reports_dir, "full_dataset_summary.txt"), "w") as f:
            f.write("====================================================\n")
            f.write("FULL MEDICATION INVENTORY SUMMARY REPORT\n")
            f.write("====================================================\n\n")
            f.write(f"Total Unique Medication Records : {full_summary['total_records']}\n")
            f.write(f"Total Stock Units Across Facility: {full_summary['total_items_in_stock']:,}\n")
            f.write(f"Total Valuation of Inventory     : ${full_summary['total_inventory_value']:,.2f}\n")
            f.write(f"Critical Status Medication Count : {full_summary['critical_items_count']}\n\n")
            f.write("--- STATISTICAL DESCRIPTIONS ---\n")
            f.write(full_summary["numeric_summary"].to_string())
            f.write("\n")

        # 30-Day Expiring Summary
        with open(os.path.join(self.reports_dir, "expiring_30_days_summary.txt"), "w") as f:
            f.write("====================================================\n")
            f.write("30-DAY EXPIRING MEDICATION ACTION REPORT\n")
            f.write("====================================================\n\n")
            f.write(f"Medications Expiring in <= 30 Days: {exp_summary['count']}\n")
            f.write(f"Percentage of Total Inventory Data : {exp_summary['pct_of_total']}%\n")
            f.write(f"Total Stock Valuation At Risk     : ${exp_summary['total_value_at_risk']:,.2f}\n")
            f.write(f"High-Priority / Critical Items    : {exp_summary['critical_count']}\n")
            f.write(f"Affected Therapeutic Categories   : {exp_summary['categories_affected']}\n")

    def export_expiring_csv_and_excel(self):
        """Export expiring dataset to CSV and Excel format."""
        cols = [
            "Medication ID", "Medication Name", "Generic Name", "Category",
            "Expiration Date", "Days Until Expiry", "Quantity in Stock",
            "Unit Cost", "Total Stock Value", "Critical Status", "Storage Location"
        ]
        export_df = self.exp_df[cols].copy()

        # CSV Export
        export_df.to_csv(os.path.join(self.reports_dir, "expiring_medications_detailed.csv"), index=False)

        # Excel Export (Google Sheets Ready)
        excel_path = os.path.join(self.output_dir, "medication_expiring_30d.xlsx")
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            export_df.to_excel(writer, sheet_name="Expiring_30_Days", index=False)

    def build_interactive_html(self):
        """Create a single-file, interactive HTML dashboard using Plotly."""
        # Visual 1: Interactive Expiry Timeline
        timeline_df = self.exp_df.groupby("Expiration Date").size().reset_index(name="Count")
        fig1 = px.line(
            timeline_df, x="Expiration Date", y="Count",
            title="Daily Expiry Timeline (Next 30 Days)",
            markers=True, line_shape="spline", color_discrete_sequence=["#e74c3c"]
        )

        # Visual 2: Category Breakdown
        fig2 = px.histogram(
            self.exp_df, x="Category", color="Critical Status",
            title="Expiring Items by Category & Criticality",
            barmode="group", color_discrete_map={True: "#e74c3c", False: "#3498db"}
        )

        # Visual 3: Treemap
        fig3 = px.treemap(
            self.exp_df, path=["Manufacturer", "Category", "Medication Name"],
            values="Quantity in Stock", color="Total Stock Value",
            title="Expiring Stock Treemap (Size=Qty, Color=Value)", color_continuous_scale="Reds"
        )

        # Convert Plotly figures to HTML divs
        div1 = fig1.to_html(full_html=False, include_plotlyjs="cdn")
        div2 = fig2.to_html(full_html=False, include_plotlyjs=False)
        div3 = fig3.to_html(full_html=False, include_plotlyjs=False)

        # Build Interactive HTML Table
        table_rows = ""
        for _, row in self.exp_df.iterrows():
            crit_badge = '<span style="color:red; font-weight:bold;">CRITICAL</span>' if row["Critical Status"] else "Standard"
            table_rows += f"""
            <tr>
                <td>{row['Medication ID']}</td>
                <td>{row['Medication Name']}</td>
                <td>{row['Category']}</td>
                <td>{row['Expiration Date'].strftime('%Y-%m-%d')}</td>
                <td><b>{row['Days Until Expiry']}</b></td>
                <td>{row['Quantity in Stock']}</td>
                <td>${row['Total Stock Value']:,.2f}</td>
                <td>{crit_badge}</td>
                <td>{row['Storage Location']}</td>
            </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Medication Expiry Executive Dashboard</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f8f9fa; }}
                h1 {{ color: #2c3e50; text-align: center; }}
                .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 22%; display: inline-block; margin: 1%; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #e74c3c; }}
                .chart-container {{ background: white; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }}
                th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
                th {{ background-color: #34495e; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Medication Inventory Expiry Analysis (30-Day Outlook)</h1>

            <div>
                <div class="metric-card">
                    <div>Expiring Items</div>
                    <div class="metric-value">{len(self.exp_df)}</div>
                </div>
                <div class="metric-card">
                    <div>At-Risk Value</div>
                    <div class="metric-value">${self.exp_df['Total Stock Value'].sum():,.2f}</div>
                </div>
                <div class="metric-card">
                    <div>Critical Items At-Risk</div>
                    <div class="metric-value">{self.exp_df['Critical Status'].sum()}</div>
                </div>
                <div class="metric-card">
                    <div>Total Units At-Risk</div>
                    <div class="metric-value">{self.exp_df['Quantity in Stock'].sum():,}</div>
                </div>
            </div>

            <div class="chart-container">{div1}</div>
            <div class="chart-container">{div2}</div>
            <div class="chart-container">{div3}</div>

            <div class="chart-container">
                <h2>Expiring Medications Detailed Table</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Med ID</th>
                            <th>Medication Name</th>
                            <th>Category</th>
                            <th>Expiry Date</th>
                            <th>Days Left</th>
                            <th>Qty</th>
                            <th>Total Value</th>
                            <th>Status</th>
                            <th>Location</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """

        with open(os.path.join(self.html_dir, "final_report.html"), "w", encoding="utf-8") as f:
            f.write(html_content)