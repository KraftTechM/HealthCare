"""Module for statistical and transactional analysis of medication inventory data."""

from datetime import datetime
import numpy as np
import pandas as pd


class InventoryAnalyzer:
    """Provides analytical capabilities over medication data."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df["Expiration Date"] = pd.to_datetime(self.df["Expiration Date"])
        self.df["Date Received"] = pd.to_datetime(self.df["Date Received"])
        self.df["Total Stock Value"] = self.df["Quantity in Stock"] * self.df["Unit Cost"]
        self.today = pd.to_datetime(datetime.now().date())
        self.df["Days Until Expiry"] = (self.df["Expiration Date"] - self.today).dt.days

    def get_full_summary(self) -> dict:
        """Compute full dataset summary statistics."""
        numeric_summary = self.df[["Quantity in Stock", "Unit Cost", "Total Stock Value", "Days Until Expiry"]].describe().T
        cat_counts = self.df["Category"].value_counts().to_dict()
        critical_count = int(self.df["Critical Status"].sum())

        return {
            "total_records": len(self.df),
            "total_inventory_value": float(self.df["Total Stock Value"].sum()),
            "total_items_in_stock": int(self.df["Quantity in Stock"].sum()),
            "critical_items_count": critical_count,
            "numeric_summary": numeric_summary,
            "category_counts": cat_counts
        }

    def get_expiring_within_30_days(self) -> pd.DataFrame:
        """Filter dataset for items expiring within 30 days (0 to 30 days inclusive)."""
        mask = (self.df["Days Until Expiry"] >= 0) & (self.df["Days Until Expiry"] <= 30)
        expiring_df = self.df[mask].copy().sort_values("Days Until Expiry")
        return expiring_df

    def get_expiring_summary(self) -> dict:
        """Summary metrics specifically for expiring items."""
        exp_df = self.get_expiring_within_30_days()
        return {
            "count": len(exp_df),
            "pct_of_total": round((len(exp_df) / len(self.df)) * 100, 2),
            "total_value_at_risk": float(exp_df["Total Stock Value"].sum()),
            "critical_count": int(exp_df["Critical Status"].sum()),
            "categories_affected": exp_df["Category"].nunique()
        }