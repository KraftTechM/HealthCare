"""Module for generating realistic synthetic medication inventory data."""

import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


class SyntheticDataGenerator:
    """Generates synthetic medication inventory dataset conforming to clinical/inventory rules."""

    DRUG_POOL = [
        ("Amoxicillin", "Amoxicillin", "Antibiotic", "500mg", "Capsule"),
        ("Azithromycin", "Azithromycin", "Antibiotic", "250mg", "Tablet"),
        ("Ciprofloxacin", "Ciprofloxacin", "Antibiotic", "500mg", "Tablet"),
        ("Cephalexin", "Cephalexin", "Antibiotic", "250mg", "Capsule"),
        ("Doxycycline", "Doxycycline", "Antibiotic", "100mg", "Capsule"),
        ("Metformin", "Metformin", "Antidiabetic", "500mg", "Tablet"),
        ("Glipizide", "Glipizide", "Antidiabetic", "5mg", "Tablet"),
        ("Insulin Glargine", "Insulin Glargine", "Antidiabetic", "100units/ml", "Injection"),
        ("Lisinopril", "Lisinopril", "Antihypertensive", "10mg", "Tablet"),
        ("Amlodipine", "Amlodipine", "Antihypertensive", "5mg", "Tablet"),
        ("Losartan", "Losartan", "Antihypertensive", "50mg", "Tablet"),
        ("Metoprolol Tartrate", "Metoprolol", "Antihypertensive", "25mg", "Tablet"),
        ("Atorvastatin", "Atorvastatin", "Antihyperlipidemic", "20mg", "Tablet"),
        ("Simvastatin", "Simvastatin", "Antihyperlipidemic", "10mg", "Tablet"),
        ("Rosuvastatin", "Rosuvastatin", "Antihyperlipidemic", "10mg", "Tablet"),
        ("Omeprazole", "Omeprazole", "Gastrointestinal", "20mg", "Capsule"),
        ("Pantoprazole", "Pantoprazole", "Gastrointestinal", "40mg", "Tablet"),
        ("Famotidine", "Famotidine", "Gastrointestinal", "20mg", "Tablet"),
        ("Albuterol", "Albuterol", "Respiratory", "90mcg", "Inhaler"),
        ("Fluticasone", "Fluticasone", "Respiratory", "50mcg", "Spray"),
        ("Montelukast", "Montelukast", "Respiratory", "10mg", "Tablet"),
        ("Ibuprofen", "Ibuprofen", "Analgesic/NSAID", "400mg", "Tablet"),
        ("Acetaminophen", "Acetaminophen", "Analgesic", "500mg", "Tablet"),
        ("Naproxen", "Naproxen", "Analgesic/NSAID", "250mg", "Tablet"),
        ("Meloxicam", "Meloxicam", "Analgesic/NSAID", "15mg", "Tablet"),
        ("Tramadol", "Tramadol", "Analgesic", "50mg", "Tablet"),
        ("Gabapentin", "Gabapentin", "Neurological", "300mg", "Capsule"),
        ("Pregabalin", "Pregabalin", "Neurological", "75mg", "Capsule"),
        ("Sertraline", "Sertraline", "Psychiatric", "50mg", "Tablet"),
        ("Escitalopram", "Escitalopram", "Psychiatric", "10mg", "Tablet"),
        ("Fluoxetine", "Fluoxetine", "Psychiatric", "20mg", "Capsule"),
        ("Alprazolam", "Alprazolam", "Psychiatric", "0.5mg", "Tablet"),
        ("Lorazepam", "Lorazepam", "Psychiatric", "1mg", "Tablet"),
        ("Levothyroxine", "Levothyroxine", "Endocrine", "50mcg", "Tablet"),
        ("Prednisone", "Prednisone", "Corticosteroid", "10mg", "Tablet"),
        ("Hydrochlorothiazide", "Hydrochlorothiazide", "Diuretic", "25mg", "Tablet"),
        ("Furosemide", "Furosemide", "Diuretic", "20mg", "Tablet"),
        ("Warfarin", "Warfarin", "Anticoagulant", "5mg", "Tablet"),
        ("Rivaroxaban", "Rivaroxaban", "Anticoagulant", "15mg", "Tablet"),
        ("Apixaban", "Apixaban", "Anticoagulant", "5mg", "Tablet"),
        ("Ondansetron", "Ondansetron", "Antiemetic", "4mg", "Tablet"),
        ("Hydrocodone/Acetaminophen", "Hydrocodone/APAP", "Analgesic", "5/325mg", "Tablet"),
        ("Cyclobenzaprine", "Cyclobenzaprine", "Muscle Relaxant", "10mg", "Tablet"),
        ("Trazodone", "Trazodone", "Psychiatric", "50mg", "Tablet"),
        ("Duloxetine", "Duloxetine", "Psychiatric", "30mg", "Capsule"),
        ("Venlafaxine", "Venlafaxine", "Psychiatric", "75mg", "Capsule"),
        ("Ranitidine", "Ranitidine", "Gastrointestinal", "150mg", "Tablet"),
        ("Clopidogrel", "Clopidogrel", "Antiplatelet", "75mg", "Tablet"),
        ("Allopurinol", "Allopurinol", "Antigout", "100mg", "Tablet"),
        ("Hydrocortisone Cream", "Hydrocortisone", "Dermatological", "1%", "Cream"),
        ("Triamcinolone", "Triamcinolone", "Dermatological", "0.1%", "Ointment"),
        ("Amoxicillin/Clavulanate", "Amoxicillin/Clav", "Antibiotic", "875mg", "Tablet"),
        ("Azelastine", "Azelastine", "Antihistamine", "0.1%", "Spray"),
        ("Cetirizine", "Cetirizine", "Antihistamine", "10mg", "Tablet"),
        ("Loratadine", "Loratadine", "Antihistamine", "10mg", "Tablet"),
    ]

    MANUFACTURERS = [
        "Pfizer Inc.", "Novartis AG", "Roche Holding", "Merck & Co.",
        "AbbVie Inc.", "Johnson & Johnson", "Sanofi S.A.", "Bristol Myers Squibb",
        "AstraZeneca PLC", "GSK plc", "Teva Pharmaceutical", "Sandoz"
    ]

    SUPPLIERS = [
        "McKesson Corporation", "AmerisourceBergen", "Cardinal Health",
        "Medline Industries", "Henry Schein", "Owens & Minor"
    ]

    STORAGE_LOCATIONS = [
        "Aisle 1 - Shelf A", "Aisle 1 - Shelf B", "Aisle 2 - Shelf A",
        "Aisle 2 - Shelf C", "Main Refrigerator A", "Main Refrigerator B",
        "Controlled Vault 1", "Narcotics Safe B", "Aisle 3 - Shelf D"
    ]

    def __init__(self, seed: int = 42):
        """Initialize generator with random seed."""
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def generate(self, count: int = 1000) -> pd.DataFrame:
        """Generate synthetic dataset.

        Args:
            count: Number of rows to generate.

        Returns:
            pd.DataFrame: Completed medication dataset.
        """
        data = []
        today = datetime.now()

        for i in range(1, count + 1):
            med_id = f"MED-{i:05d}"
            drug = random.choice(self.DRUG_POOL)
            brand_name, generic_name, category, dosage, form = drug

            mfg = random.choice(self.MANUFACTURERS)
            supplier = random.choice(self.SUPPLIERS)
            location = random.choice(self.STORAGE_LOCATIONS)
            batch = f"BATCH-{random.randint(2022, 2026)}-{random.randint(10000, 99999)}"

            critical_status = category in [
                "Anticoagulant", "Antidiabetic", "Respiratory", "Antihypertensive"
            ] or (random.random() < 0.25)

            # Expiry date distribution logic
            rand_val = random.random()
            if rand_val < 0.02:  # 2% Expired (-30 to -1 days)
                days_offset = random.randint(-30, -1)
            elif rand_val < 0.10:  # 8% Expiring in 1-30 days
                days_offset = random.randint(1, 30)
            elif rand_val < 0.30:  # 20% Expiring in 31-90 days
                days_offset = random.randint(31, 90)
            else:  # 70% Expiring in 91-730 days
                days_offset = random.randint(91, 730)

            exp_date = (today + timedelta(days=days_offset)).date()
            date_received = (today - timedelta(days=random.randint(1, 180))).date()

            quantity = int(np.random.gamma(shape=3.0, scale=40.0)) + 10
            quantity = min(max(quantity, 10), 500)

            unit_cost = round(float(np.random.exponential(scale=35.0)) + 0.50, 2)
            unit_cost = min(max(unit_cost, 0.50), 500.00)

            data.append({
                "Medication ID": med_id,
                "Medication Name": brand_name,
                "Generic Name": generic_name,
                "Category": category,
                "Dosage": dosage,
                "Form": form,
                "Manufacturer": mfg,
                "Batch Number": batch,
                "Quantity in Stock": quantity,
                "Expiration Date": exp_date,
                "Storage Location": location,
                "Unit Cost": unit_cost,
                "Supplier": supplier,
                "Date Received": date_received,
                "Critical Status": critical_status
            })

        df = pd.DataFrame(data)
        return df