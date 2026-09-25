from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"


def main():
    file_path = DATA_DIR / "classData.csv"

    print("=" * 70)
    print("PRJ_232 - FAULT LABEL ANALYSIS")
    print("=" * 70)

    df = pd.read_csv(file_path)

    # ---------------------------------------------------------
    # 1. Show fault indicator columns
    # ---------------------------------------------------------

    fault_columns = ["A", "B", "C", "G"]

    print("\nFault indicator columns:")
    print(fault_columns)

    # ---------------------------------------------------------
    # 2. Count every A/B/C/G combination
    # ---------------------------------------------------------

    print("\nFault combinations:")
    print("-" * 70)

    combinations = (
        df[fault_columns]
        .value_counts()
        .reset_index(name="count")
    )

    print(combinations.to_string(index=False))

    # ---------------------------------------------------------
    # 3. Create a readable fault label
    # ---------------------------------------------------------

    def get_fault_label(row):

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

        if number_of_phases == 0 and G == 0:
            return "Normal"

        if number_of_phases == 1 and G == 1:
            return "LG"

        if number_of_phases == 2 and G == 0:
            return "LL"

        if number_of_phases == 2 and G == 1:
            return "LLG"

        if number_of_phases == 3 and G == 0:
            return "LLL"

        if number_of_phases == 3 and G == 1:
            return "LLLG"

        return "Unknown"

    df["Fault_Type"] = df.apply(get_fault_label, axis=1)

    # ---------------------------------------------------------
    # 4. Count the six fault categories
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("FAULT CATEGORY DISTRIBUTION")
    print("=" * 70)

    distribution = df["Fault_Type"].value_counts()

    print(distribution.to_string())

    # ---------------------------------------------------------
    # 5. Show percentages
    # ---------------------------------------------------------

    print("\nFault percentages:")

    percentages = (
        df["Fault_Type"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )

    for fault_type, percentage in percentages.items():
        print(f"{fault_type:6} : {percentage:.2f}%")

    # ---------------------------------------------------------
    # 6. Check for unknown combinations
    # ---------------------------------------------------------

    unknown_count = (df["Fault_Type"] == "Unknown").sum()

    print("\nUnknown combinations:", unknown_count)

    # ---------------------------------------------------------
    # 7. Check target leakage
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("PROPOSED ML FEATURES")
    print("=" * 70)

    features = [
        "Ia",
        "Ib",
        "Ic",
        "Va",
        "Vb",
        "Vc"
    ]

    print(features)

    print("\nTarget:")
    print("Fault_Type")

    print("\nFault indicator columns A/B/C/G will NOT be used")
    print("as ML input features because they directly define")
    print("the fault condition.")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()