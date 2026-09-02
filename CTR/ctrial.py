import json
import os
import pandas as pd

# ==========================================================
# SECTION 1: DATA LOADING & EXTRACTION
# ==========================================================


def extract_trial_data(folder_path="."):
    """Reads all JSON files in the specified directory and extracts

    key clinical trial fields including PI details and location data.
    """
    data_list = []

    # Iterate through all files in the current folder
    for filename in os.listdir(folder_path):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(folder_path, filename)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as e:
            print(f"⚠️ Error reading {filename}: {e}")
            continue

        # ClinicalTrials.gov exports can contain one record or a list of records.
        records = data if isinstance(data, list) else [data]
        for record in records:
            if not isinstance(record, dict):
                continue

            protocol = record.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            desc_module = protocol.get("descriptionModule", {})
            contacts_locations = protocol.get("contactsLocationsModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            responsible_party = sponsor_module.get("responsibleParty", {})

            nct_id = id_module.get("nctId", "N/A")
            detailed_description = desc_module.get("detailedDescription", "")
            study_title = id_module.get("briefTitle", "N/A")
            overall_status = status_module.get("overallStatus", "N/A")
            study_type = design_module.get("studyType", "N/A")
            phases = design_module.get("phases", [])
            phases = ", ".join(phases) if isinstance(phases, list) else phases
            enrollment = design_module.get("enrollmentInfo", {}).get("count")
            enrollment = pd.to_numeric(enrollment, errors="coerce")

            pi, role, affiliation = "N/A", "N/A", "N/A"
            overall_officials = contacts_locations.get("overallOfficials", [])
            if overall_officials and isinstance(overall_officials, list):
                pi_info = overall_officials[0]
                pi = pi_info.get("name", "N/A")
                role = pi_info.get("role", "N/A")
                affiliation = pi_info.get("affiliation", "N/A")
            elif isinstance(responsible_party, dict):
                pi = responsible_party.get("investigatorFullName", "N/A")
                role = responsible_party.get("investigatorTitle", "N/A")
                affiliation = responsible_party.get("investigatorAffiliation", "N/A")

            locations = contacts_locations.get("locations", [])
            locations = locations if isinstance(locations, list) else []
            locations = locations or [{}]
            for loc in locations:
                data_list.append(
                    {
                        "nct_id": nct_id,
                        "study_title": study_title,
                        "overall_status": overall_status,
                        "study_type": study_type,
                        "phases": phases,
                        "enrollment": enrollment,
                        "facility": loc.get("facility", "N/A"),
                        "city": loc.get("city", "N/A"),
                        "country": loc.get("country", "N/A"),
                        "pi": pi,
                        "role": role,
                        "affiliation": affiliation,
                        "detailed_description": detailed_description,
                    }
                )

    return pd.DataFrame(data_list)


# ==========================================================
# SECTION 2: USER INTERACTION & SEARCH FILTER
# ==========================================================


def summarize_trials(df):
    """Print high-level study and location statistics for the loaded dataset."""
    if df.empty:
        print("No trial data available for summary.")
        return

    studies = df.drop_duplicates("nct_id")
    locations = df[df["country"] != "N/A"]

    print("\n--- Dataset Summary ---")
    print(f"Unique studies: {studies['nct_id'].nunique():,}")
    print(f"Study-location rows: {len(locations):,}")
    print(f"Countries represented: {locations['country'].nunique():,}")
    print("\nTop study statuses:")
    print(studies["overall_status"].value_counts().head(8).to_string())
    print("\nTop countries by location count:")
    print(locations["country"].value_counts().head(8).to_string())


def filter_trials(df):
    """Filter trials by a case-insensitive country name entered by the user."""
    if df.empty:
        print("❌ No trial data extracted. Ensure JSON files are in the directory.")
        return df

    print("\n--- Clinical Trials Search Engine ---")
    search_country = input("Enter Country: ").strip().lower()

    filtered_df = df.copy()

    # Case-insensitive partial matching
    if not search_country:
        print("Please enter a country name.")
        return pd.DataFrame()

    filtered_df = filtered_df[
        filtered_df["country"].str.lower().str.contains(search_country, na=False, regex=False)
    ]

    print(f"\n✅ Search complete! Found {len(filtered_df)} matching record(s).\n")
    return filtered_df


def display_country_results(df):
    """Print city, location, status, and enrollment information for one country."""
    valid = df[(df["city"] != "N/A") & (df["country"] != "N/A")].copy()
    if valid.empty:
        print("No city-level location data found for this country.")
        return

    study_city = valid.drop_duplicates(["nct_id", "city"])
    city_summary = valid.groupby("city").size().rename("locations").to_frame()
    city_summary["studies"] = study_city.groupby("city")["nct_id"].nunique()
    city_summary["enrollment"] = study_city.groupby("city")["enrollment"].sum()
    city_summary = city_summary.sort_values(
        ["locations", "studies"], ascending=False
    ).reset_index()
    print("\n--- Cities and Trial Information ---")
    print(city_summary.head(25).to_string(index=False))
    print("\nStudy statuses:")
    print(valid.drop_duplicates("nct_id")["overall_status"].value_counts().to_string())


# ==========================================================
# SECTION 3: VISUALIZATION MODULE
# ==========================================================


def generate_trial_plots(df):
    """Plot city locations, statuses, and enrollment for the selected country."""
    if df.empty:
        print("⚠️ No data available to display plots.")
        return

    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("⚠️ Plotting requires matplotlib and seaborn. Install them with: pip install matplotlib seaborn")
        return

    plot_df = df[(df["country"] != "N/A") & (df["city"] != "N/A")].copy()

    if plot_df.empty:
        print("⚠️ Not enough valid location data to generate plots.")
        return

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    country = plot_df["country"].mode().iat[0]
    fig.suptitle(
        f"Clinical Trials Investigation: {country}",
        fontsize=16,
        fontweight="bold",
    )

    # Plot 1: Cities by location count
    top_cities = plot_df["city"].value_counts().head(12).sort_values()
    sns.barplot(
        x=top_cities.values,
        y=top_cities.index,
        ax=axes[0, 0],
        palette="viridis",
        hue=top_cities.index,
        legend=False,
    )
    axes[0, 0].set_title("Cities by Location Count", fontweight="bold")
    axes[0, 0].set_xlabel("Number of Locations")

    # Plot 2: Study status
    statuses = plot_df.drop_duplicates("nct_id")["overall_status"].value_counts().head(10).sort_values()
    sns.barplot(
        x=statuses.values,
        y=statuses.index,
        ax=axes[0, 1],
        palette="magma",
        hue=statuses.index,
        legend=False,
    )
    axes[0, 1].set_title("Studies by Status", fontweight="bold")
    axes[0, 1].set_xlabel("Number of Studies")

    # Plot 3: Estimated enrollment by city, counting each study once per city.
    city_enrollment = (
        plot_df.drop_duplicates(["nct_id", "city"])
        .groupby("city")["enrollment"]
        .sum()
        .sort_values()
        .tail(12)
    )
    sns.barplot(
        x=city_enrollment.values,
        y=city_enrollment.index,
        ax=axes[1, 0],
        palette="crest",
        hue=city_enrollment.index,
        legend=False,
    )
    axes[1, 0].set_title("Estimated Enrollment by City", fontweight="bold")
    axes[1, 0].set_xlabel("Participants")

    # Plot 4: Enrollment distribution across unique studies.
    enrollments = plot_df.drop_duplicates("nct_id")["enrollment"].dropna()
    if enrollments.empty:
        axes[1, 1].text(0.5, 0.5, "No Enrollment Data", ha="center", va="center")
    else:
        sns.histplot(enrollments, bins=20, ax=axes[1, 1], color="#287c8e")
        axes[1, 1].set_title("Study Enrollment Distribution", fontweight="bold")
        axes[1, 1].set_xlabel("Estimated Participants")
        axes[1, 1].set_ylabel("Number of Studies")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()


# ==========================================================
# SECTION 4: MAIN EXECUTION PIPELINE
# ==========================================================


def main():
    # Step 1: Parse JSON files
    raw_df = extract_trial_data()

    # Step 2: Show the shape of the loaded dataset
    summarize_trials(raw_df)

    # Step 3: Apply user filters
    filtered_df = filter_trials(raw_df)

    # Step 4: Print summary preview to VS Code terminal
    if not filtered_df.empty:
        display_country_results(filtered_df)

        # Step 5: Ask user if they want to save results
        save_csv = (
            input("\nSave filtered results to CSV file? (y/n): ")
            .strip()
            .lower()
        )
        if save_csv == "y":
            filtered_df.to_csv("filtered_clinical_trials.csv", index=False)
            print("💾 Saved results to 'filtered_clinical_trials.csv'.")

        # Step 6: Render Plots
        generate_trial_plots(filtered_df)


if __name__ == "__main__":
    main()