from pathlib import Path
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"


# ============================================================
# FAULT LABEL CREATION
# ============================================================

def get_fault_label(row):
    """
    Convert the A/B/C/G fault indicators into a
    six-class fault label.

    A, B, C = affected phases
    G       = ground involvement
    """

    A = row["A"]
    B = row["B"]
    C = row["C"]
    G = row["G"]

    phases = []

    if A == 1:
        phases.append("A")

    if B == 1:
        phases.append("B")

    if C == 1:
        phases.append("C")

    number_of_phases = len(phases)

    # Normal
    if number_of_phases == 0 and G == 0:
        return "Normal"

    # Single phase to ground
    if number_of_phases == 1 and G == 1:
        return "LG"

    # Two phases
    if number_of_phases == 2 and G == 0:
        return "LL"

    # Two phases to ground
    if number_of_phases == 2 and G == 1:
        return "LLG"

    # Three phases
    if number_of_phases == 3 and G == 0:
        return "LLL"

    # Three phases to ground
    if number_of_phases == 3 and G == 1:
        return "LLLG"

    return "Unknown"


# ============================================================
# MAIN ANALYSIS
# ============================================================

def main():

    print("=" * 70)
    print("PRJ_232 - DATASET STRUCTURE ANALYSIS")
    print("=" * 70)

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    file_path = DATA_DIR / "classData.csv"

    print("\nLoading dataset:")
    print(file_path)

    if not file_path.exists():
        print("\nERROR: classData.csv was not found.")
        print("Expected location:")
        print(file_path)
        return

    df = pd.read_csv(file_path)

    print("\nDataset loaded successfully.")

    # --------------------------------------------------------
    # Create fault labels
    # --------------------------------------------------------

    df["Fault_Type"] = df.apply(get_fault_label, axis=1)

    # --------------------------------------------------------
    # Dataset size
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("DATASET SIZE")
    print("=" * 70)

    print(f"Rows    : {len(df)}")
    print(f"Columns : {len(df.columns)}")

    # --------------------------------------------------------
    # First 30 fault labels
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FIRST 30 FAULT LABELS")
    print("=" * 70)

    print(
        df["Fault_Type"]
        .head(30)
        .to_string(index=True)
    )

    # --------------------------------------------------------
    # Number of transitions
    # --------------------------------------------------------

    # A transition occurs whenever the current fault label
    # differs from the previous row.

    transitions = (
        df["Fault_Type"]
        .ne(df["Fault_Type"].shift())
        .sum()
        - 1
    )

    print("\nNumber of fault-type transitions:")
    print(transitions)

    # --------------------------------------------------------
    # Create run IDs
    # --------------------------------------------------------

    # Each consecutive block of the same fault type receives
    # a unique run ID.

    run_id = (
        df["Fault_Type"]
        .ne(df["Fault_Type"].shift())
        .cumsum()
    )

    df["Run_ID"] = run_id

    # --------------------------------------------------------
    # Consecutive run information
    # --------------------------------------------------------

    runs = (
        df.groupby(["Run_ID", "Fault_Type"])
        .size()
        .reset_index(name="samples")
    )

    print("\n" + "=" * 70)
    print("CONSECUTIVE FAULT RUNS")
    print("=" * 70)

    print(runs.to_string(index=False))

    # --------------------------------------------------------
    # Run statistics by fault class
    # --------------------------------------------------------

    run_statistics = (
        runs.groupby("Fault_Type")["samples"]
        .agg(
            number_of_runs="count",
            minimum_samples="min",
            maximum_samples="max",
            average_samples="mean"
        )
        .round(2)
    )

    print("\n" + "=" * 70)
    print("CONSECUTIVE RUN STATISTICS")
    print("=" * 70)

    print(run_statistics)

    # --------------------------------------------------------
    # Feature list
    # --------------------------------------------------------

    features = [
        "Ia",
        "Ib",
        "Ic",
        "Va",
        "Vb",
        "Vc"
    ]

    # --------------------------------------------------------
    # Feature ranges
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FEATURE RANGES")
    print("=" * 70)

    feature_statistics = (
        df[features]
        .describe()
        .T[
            [
                "min",
                "max",
                "mean",
                "std"
            ]
        ]
        .round(4)
    )

    print(feature_statistics)

    # --------------------------------------------------------
    # Feature means by fault class
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FEATURE MEANS BY FAULT CLASS")
    print("=" * 70)

    feature_means = (
        df.groupby("Fault_Type")[features]
        .mean()
        .round(4)
    )

    print(feature_means)

    # --------------------------------------------------------
    # Feature standard deviations by fault class
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FEATURE STANDARD DEVIATIONS BY FAULT CLASS")
    print("=" * 70)

    feature_std = (
        df.groupby("Fault_Type")[features]
        .std()
        .round(4)
    )

    print(feature_std)

    # --------------------------------------------------------
    # Class distribution
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FAULT CLASS DISTRIBUTION")
    print("=" * 70)

    class_counts = (
        df["Fault_Type"]
        .value_counts()
        .rename_axis("Fault_Type")
        .reset_index(name="Samples")
    )

    class_counts["Percentage"] = (
        class_counts["Samples"]
        / len(df)
        * 100
    ).round(2)

    print(class_counts.to_string(index=False))

    # --------------------------------------------------------
    # Unknown labels
    # --------------------------------------------------------

    unknown_count = (
        df["Fault_Type"] == "Unknown"
    ).sum()

    print("\nUnknown fault labels:")
    print(unknown_count)

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("MISSING VALUES")
    print("=" * 70)

    missing_values = df[features].isnull().sum()

    print(missing_values)

    # --------------------------------------------------------
    # Duplicate rows
    # --------------------------------------------------------

    print("\nDuplicate rows:")
    print(df.duplicated().sum())

    # --------------------------------------------------------
    # Correlation matrix
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FEATURE CORRELATION MATRIX")
    print("=" * 70)

    correlation = (
        df[features]
        .corr()
        .round(3)
    )

    print(correlation)

    # --------------------------------------------------------
    # Final interpretation information
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("PROPOSED MACHINE-LEARNING SETUP")
    print("=" * 70)

    print("\nInput features:")
    for feature in features:
        print(f"  - {feature}")

    print("\nTarget:")
    print("  - Fault_Type")

    print("\nExcluded from ML features:")
    print("  - A")
    print("  - B")
    print("  - C")
    print("  - G")

    print(
        "\nReason: A/B/C/G directly encode the fault condition "
        "and would cause target leakage."
    )

    print("\n" + "=" * 70)
    print("DATASET STRUCTURE ANALYSIS COMPLETE")
    print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()