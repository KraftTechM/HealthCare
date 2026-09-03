"""Master Orchestration Script for Medication Inventory Analysis Pipeline."""

import os
import sys
from analyzer import InventoryAnalyzer
from data_generator import SyntheticDataGenerator
from report_generator import ReportGenerator
from visualizer import InventoryVisualizer


def main():
    print("====================================================")
    print("  MEDICATION INVENTORY PIPELINE INITIALIZATION     ")
    print("====================================================")

    # 1. Base Setup
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "output")
    raw_dir = os.path.join(output_dir, "raw_data")
    os.makedirs(raw_dir, exist_ok=True)

    # 2. Data Generation
    print("[1/4] Generating 1,000 synthetic medication records...")
    generator = SyntheticDataGenerator(seed=42)
    df = generator.generate(count=1000)
    raw_data_path = os.path.join(raw_dir, "medication_inventory.csv")
    df.to_csv(raw_data_path, index=False)
    print(f"      -> Synthetic data saved to: {raw_data_path}")

    # 3. Data Analysis
    print("[2/4] Performing inventory & expiry analysis...")
    analyzer = InventoryAnalyzer(df)
    full_summary = analyzer.get_full_summary()
    exp_df = analyzer.get_expiring_within_30_days()
    exp_summary = analyzer.get_expiring_summary()

    print(f"      -> Total Items: {full_summary['total_records']}")
    print(f"      -> Expiring in 30 Days: {exp_summary['count']} ({exp_summary['pct_of_total']}%)")

    # 4. Data Visualization
    print("[3/4] Generating plot assets (Full Dataset + Expiring)...")
    visualizer = InventoryVisualizer(df, output_dir)
    visualizer.generate_all_static(exp_df)
    print("      -> Visualizations successfully exported to /output/plots/")

    # 5. Report Generation
    print("[4/4] Writing text reports, Excel files, and interactive HTML...")
    reporter = ReportGenerator(df, exp_df, output_dir)
    reporter.export_text_summaries(full_summary, exp_summary)
    reporter.export_expiring_csv_and_excel()
    reporter.build_interactive_html()

    print("====================================================")
    print(" PIPELINE EXECUTION COMPLETE")
    print(f" View dashboard at: {os.path.join(output_dir, 'consolidated_report', 'final_report.html')}")
    print("====================================================")


if __name__ == "__main__":
    main()