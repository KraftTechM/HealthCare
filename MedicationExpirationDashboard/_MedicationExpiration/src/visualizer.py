"""Module for producing matplotlib/seaborn static charts and Plotly interactive charts."""

import os
import matplotlib

# This pipeline writes files and may run on a server without a desktop/Tk.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns

sns.set_theme(style="whitegrid")


class InventoryVisualizer:
    """Renders visual outputs for both full inventory and 30-day expiring analysis."""

    def __init__(self, df: pd.DataFrame, output_dir: str):
        self.df = df.copy()
        self.df["Expiration Date"] = pd.to_datetime(self.df["Expiration Date"])
        self.df["Total Stock Value"] = self.df["Quantity in Stock"] * self.df["Unit Cost"]
        self.today = pd.to_datetime("today").normalize()
        self.df["Days Until Expiry"] = (self.df["Expiration Date"] - self.today).dt.days
        self.output_dir = output_dir

        self.full_plots_dir = os.path.join(output_dir, "plots", "full_dataset_analysis")
        self.exp_plots_dir = os.path.join(output_dir, "plots", "expiring_30_days")
        os.makedirs(self.full_plots_dir, exist_ok=True)
        os.makedirs(self.exp_plots_dir, exist_ok=True)

    # ------------------ Part A: Full Dataset Plots ------------------

    def plot_stock_distribution_by_category(self):
        """Histogram/Bar plot of quantities by category."""
        plt.figure(figsize=(12, 6))
        category_qty = self.df.groupby("Category")["Quantity in Stock"].sum().sort_values(ascending=False).reset_index()
        sns.barplot(data=category_qty, x="Quantity in Stock", y="Category", hue="Category", palette="Blues_r", legend=False)
        plt.title("Total Stock Quantity by Category", fontsize=14, fontweight="bold")
        plt.xlabel("Total Units in Stock", fontsize=11)
        plt.ylabel("Category", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.full_plots_dir, "stock_distribution_by_category.png"), dpi=300)
        plt.close()

    def plot_box_by_expiration_month(self):
        """Box plot showing distribution by expiration month."""
        df_temp = self.df.copy()
        df_temp["Expiration Month"] = df_temp["Expiration Date"].dt.to_period("M").astype(str)
        top_months = df_temp["Expiration Month"].value_counts().head(12).index.tolist()
        df_filtered = df_temp[df_temp["Expiration Month"].isin(sorted(top_months))]

        plt.figure(figsize=(14, 6))
        sns.boxplot(data=df_filtered, x="Expiration Month", y="Quantity in Stock", hue="Expiration Month", palette="Set3", legend=False)
        plt.xticks(rotation=45)
        plt.title("Stock Quantity Distribution by Expiration Month", fontsize=14, fontweight="bold")
        plt.xlabel("Expiration Month", fontsize=11)
        plt.ylabel("Quantity in Stock", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.full_plots_dir, "expiration_month_boxplot.png"), dpi=300)
        plt.close()

    def plot_top20_value_medications(self):
        """Bar chart of top 20 medications by total stock value."""
        plt.figure(figsize=(12, 7))
        top20 = self.df.groupby("Medication Name")["Total Stock Value"].sum().nlargest(20).reset_index()
        sns.barplot(data=top20, x="Total Stock Value", y="Medication Name", hue="Medication Name", palette="viridis", legend=False)
        plt.title("Top 20 Medications by Total Stock Value ($)", fontsize=14, fontweight="bold")
        plt.xlabel("Total Value ($)", fontsize=11)
        plt.ylabel("Medication Name", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.full_plots_dir, "top20_stock_value.png"), dpi=300)
        plt.close()

    def plot_category_pie_chart(self):
        """Pie chart showing percentage distribution by category."""
        plt.figure(figsize=(9, 9))
        cat_counts = self.df["Category"].value_counts()
        plt.pie(cat_counts, labels=cat_counts.index, autopct="%1.1f%%", startangle=140, colors=sns.color_palette("pastel"))
        plt.title("Percentage Distribution of Records by Category", fontsize=14, fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(self.full_plots_dir, "category_distribution.png"), dpi=300)
        plt.close()

    def plot_correlation_heatmap(self):
        """Heatmap showing correlations between numeric variables."""
        plt.figure(figsize=(8, 6))
        num_cols = ["Quantity in Stock", "Unit Cost", "Total Stock Value", "Days Until Expiry"]
        corr = self.df[num_cols].corr()
        sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", vmin=-1, vmax=1, linewidths=0.5)
        plt.title("Correlation Heatmap of Numeric Variables", fontsize=14, fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(self.full_plots_dir, "correlation_heatmap.png"), dpi=300)
        plt.close()

    def plot_cost_vs_quantity_scatter(self):
        """Scatter plot: Cost vs Quantity color-coded by Critical Status."""
        plt.figure(figsize=(10, 6))
        sns.scatterplot(
            data=self.df,
            x="Unit Cost",
            y="Quantity in Stock",
            hue="Critical Status",
            palette={True: "#e74c3c", False: "#3498db"},
            alpha=0.7,
            s=60
        )
        plt.title("Unit Cost vs. Quantity in Stock (by Critical Status)", fontsize=14, fontweight="bold")
        plt.xlabel("Unit Cost ($)", fontsize=11)
        plt.ylabel("Quantity in Stock", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.full_plots_dir, "cost_vs_quantity_scatter.png"), dpi=300)
        plt.close()

    # ------------------ Part B: Expiring Within 30 Days Plots ------------------

    def plot_expiring_by_category(self, exp_df: pd.DataFrame):
        """Bar chart: Count of expiring medications by category, color-coded by critical status."""
        plt.figure(figsize=(12, 6))
        grouped = exp_df.groupby(["Category", "Critical Status"]).size().reset_index(name="Count")
        sns.barplot(
            data=grouped,
            x="Category",
            y="Count",
            hue="Critical Status",
            palette={True: "#d9534f", False: "#5bc0de"}
        )
        plt.xticks(rotation=45)
        plt.title("Expiring Medications (Next 30 Days) by Category", fontsize=14, fontweight="bold")
        plt.xlabel("Category", fontsize=11)
        plt.ylabel("Count", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.exp_plots_dir, "expiring_by_category.png"), dpi=300)
        plt.close()

    def plot_manufacturer_treemap(self, exp_df: pd.DataFrame):
        """Interactive/Static Treemap by Manufacturer and Category."""
        fig = px.treemap(
            exp_df,
            path=["Manufacturer", "Category", "Medication Name"],
            values="Quantity in Stock",
            color="Total Stock Value",
            color_continuous_scale="Reds",
            title="30-Day Expiring Inventory Treemap (Size: Stock Qty, Color: Value)"
        )
        fig.write_image(os.path.join(self.exp_plots_dir, "manufacturer_treemap.png"))
        return fig

    def plot_expiry_timeline(self, exp_df: pd.DataFrame):
        """Timeline Plot: Daily breakdown of expirations for next 30 days."""
        plt.figure(figsize=(12, 5))
        timeline_data = exp_df.groupby("Expiration Date").size().reset_index(name="Expiring Items")

        sns.lineplot(data=timeline_data, x="Expiration Date", y="Expiring Items", marker="o", color="#e67e22", linewidth=2.5)
        plt.title("Daily Expiration Timeline (Next 30 Days)", fontsize=14, fontweight="bold")
        plt.xlabel("Expiration Date", fontsize=11)
        plt.ylabel("Number of Medications Expiring", fontsize=11)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.exp_plots_dir, "expiry_timeline.png"), dpi=300)
        plt.close()

    def generate_all_static(self, exp_df: pd.DataFrame):
        """Helper to run all static matplotlib chart generations."""
        self.plot_stock_distribution_by_category()
        self.plot_box_by_expiration_month()
        self.plot_top20_value_medications()
        self.plot_category_pie_chart()
        self.plot_correlation_heatmap()
        self.plot_cost_vs_quantity_scatter()
        self.plot_expiring_by_category(exp_df)
        self.plot_manufacturer_treemap(exp_df)
        self.plot_expiry_timeline(exp_df)
