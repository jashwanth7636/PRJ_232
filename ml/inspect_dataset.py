from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"


def inspect_csv(file_name):
    file_path = DATA_DIR / file_name

    print("\n" + "=" * 70)
    print(f"FILE: {file_name}")
    print("=" * 70)

    if not file_path.exists():
        print("ERROR: File not found:")
        print(file_path)
        return

    df = pd.read_csv(file_path)

    print(f"\nFile path: {file_path}")
    print(f"Number of rows: {len(df)}")
    print(f"Number of columns: {len(df.columns)}")

    print("\nColumn names:")
    for i, column in enumerate(df.columns, start=1):
        print(f"{i:2}. {column}")

    print("\nData types:")
    print(df.dtypes)

    print("\nMissing values:")
    missing = df.isnull().sum()

    if missing.sum() == 0:
        print("No missing values found.")
    else:
        print(missing[missing > 0])

    print(f"\nDuplicate rows: {df.duplicated().sum()}")

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nUnique values per column:")

    for column in df.columns:
        unique_count = df[column].nunique()

        print(f"{column}: {unique_count} unique values")

        if unique_count <= 20:
            print(f"    Values: {df[column].unique()}")


def main():
    print("\nPRJ_232 - ELECTRICAL DATASET INSPECTION")

    inspect_csv("classData.csv")
    inspect_csv("detect_dataset.csv")

    print("\n" + "=" * 70)
    print("DATASET INSPECTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
    