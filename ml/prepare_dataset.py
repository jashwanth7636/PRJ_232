import os
import pandas as pd
from sklearn.model_selection import train_test_split


# ============================================================
# PRJ_232 - DATASET PREPARATION AND TRAIN/VALIDATION/TEST SPLIT
# ============================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "classData.csv"
)

PROCESSED_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed"
)

SPLITS_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "splits"
)


# ------------------------------------------------------------
# CREATE OUTPUT DIRECTORIES
# ------------------------------------------------------------

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(SPLITS_DIR, exist_ok=True)


print("=" * 70)
print("PRJ_232 - DATASET PREPARATION")
print("=" * 70)

print("\nLoading dataset:")
print(INPUT_FILE)


# ------------------------------------------------------------
# LOAD DATASET
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nDataset loaded successfully.")

print("\nOriginal dataset shape:")
print(f"Rows    : {df.shape[0]}")
print(f"Columns : {df.shape[1]}")


# ------------------------------------------------------------
# CREATE FAULT LABEL
# ------------------------------------------------------------

def get_fault_label(row):

    A = int(row["A"])
    B = int(row["B"])
    C = int(row["C"])
    G = int(row["G"])

    phases = A + B + C

    if phases == 0 and G == 0:
        return "Normal"

    elif phases == 1 and G == 1:
        return "LG"

    elif phases == 2 and G == 0:
        return "LL"

    elif phases == 2 and G == 1:
        return "LLG"

    elif phases == 3 and G == 0:
        return "LLL"

    elif phases == 3 and G == 1:
        return "LLLG"

    else:
        return "Unknown"


df["Fault_Type"] = df.apply(get_fault_label, axis=1)


# ------------------------------------------------------------
# CHECK LABELS
# ------------------------------------------------------------

print("\nFault classes:")

print(
    df["Fault_Type"]
    .value_counts()
    .to_string()
)


unknown_count = (df["Fault_Type"] == "Unknown").sum()

print("\nUnknown labels:")
print(unknown_count)

if unknown_count > 0:
    raise ValueError(
        "Unknown fault labels detected. Dataset preparation stopped."
    )


# ------------------------------------------------------------
# SELECT ML FEATURES
# ------------------------------------------------------------

FEATURE_COLUMNS = [
    "Ia",
    "Ib",
    "Ic",
    "Va",
    "Vb",
    "Vc"
]

TARGET_COLUMN = "Fault_Type"


# ------------------------------------------------------------
# CHECK REQUIRED COLUMNS
# ------------------------------------------------------------

required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ------------------------------------------------------------
# CREATE CLEAN DATASET
# ------------------------------------------------------------

clean_df = df[FEATURE_COLUMNS + [TARGET_COLUMN]].copy()


print("\nClean ML dataset:")
print(f"Rows    : {clean_df.shape[0]}")
print(f"Columns : {clean_df.shape[1]}")


# ------------------------------------------------------------
# CHECK MISSING VALUES
# ------------------------------------------------------------

print("\nMissing values:")

print(
    clean_df.isnull()
    .sum()
    .to_string()
)

if clean_df.isnull().sum().sum() > 0:
    raise ValueError(
        "Missing values detected. Dataset preparation stopped."
    )


# ------------------------------------------------------------
# CHECK DUPLICATES
# ------------------------------------------------------------

duplicate_count = clean_df.duplicated().sum()

print("\nDuplicate rows:")
print(duplicate_count)


# ------------------------------------------------------------
# SAVE CLEAN DATASET
# ------------------------------------------------------------

clean_dataset_path = os.path.join(
    PROCESSED_DIR,
    "clean_fault_dataset.csv"
)

clean_df.to_csv(
    clean_dataset_path,
    index=False
)

print("\nClean dataset saved:")
print(clean_dataset_path)


# ============================================================
# TRAIN / VALIDATION / TEST SPLIT
# ============================================================

print("\n" + "=" * 70)
print("TRAIN / VALIDATION / TEST SPLIT")
print("=" * 70)


X = clean_df[FEATURE_COLUMNS]

y = clean_df[TARGET_COLUMN]


# ------------------------------------------------------------
# FIRST SPLIT
# 70% TRAIN
# 30% TEMPORARY
# ------------------------------------------------------------

X_train, X_temp, y_train, y_temp = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y
)


# ------------------------------------------------------------
# SECOND SPLIT
# TEMPORARY → 15% VALIDATION + 15% TEST
# ------------------------------------------------------------

X_val, X_test, y_val, y_test = train_test_split(
    X_temp,
    y_temp,
    test_size=0.50,
    random_state=42,
    stratify=y_temp
)


# ------------------------------------------------------------
# CREATE SPLIT DATAFRAMES
# ------------------------------------------------------------

train_df = X_train.copy()
train_df[TARGET_COLUMN] = y_train

val_df = X_val.copy()
val_df[TARGET_COLUMN] = y_val

test_df = X_test.copy()
test_df[TARGET_COLUMN] = y_test


# ------------------------------------------------------------
# RESET INDEX
# ------------------------------------------------------------

train_df = train_df.reset_index(drop=True)
val_df = val_df.reset_index(drop=True)
test_df = test_df.reset_index(drop=True)


# ------------------------------------------------------------
# SAVE SPLITS
# ------------------------------------------------------------

train_path = os.path.join(
    SPLITS_DIR,
    "train.csv"
)

val_path = os.path.join(
    SPLITS_DIR,
    "validation.csv"
)

test_path = os.path.join(
    SPLITS_DIR,
    "test.csv"
)


train_df.to_csv(
    train_path,
    index=False
)

val_df.to_csv(
    val_path,
    index=False
)

test_df.to_csv(
    test_path,
    index=False
)


# ------------------------------------------------------------
# DISPLAY SPLIT SIZES
# ------------------------------------------------------------

print("\nSplit sizes:")

print(f"Training   : {len(train_df)}")
print(f"Validation : {len(val_df)}")
print(f"Testing    : {len(test_df)}")


# ------------------------------------------------------------
# DISPLAY SPLIT PERCENTAGES
# ------------------------------------------------------------

total = len(clean_df)

print("\nSplit percentages:")

print(
    f"Training   : {len(train_df) / total * 100:.2f}%"
)

print(
    f"Validation : {len(val_df) / total * 100:.2f}%"
)

print(
    f"Testing    : {len(test_df) / total * 100:.2f}%"
)


# ------------------------------------------------------------
# CLASS DISTRIBUTION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("CLASS DISTRIBUTION IN EACH SPLIT")
print("=" * 70)


print("\nTRAINING SET:")
print(
    train_df[TARGET_COLUMN]
    .value_counts()
    .sort_index()
    .to_string()
)


print("\nVALIDATION SET:")
print(
    val_df[TARGET_COLUMN]
    .value_counts()
    .sort_index()
    .to_string()
)


print("\nTEST SET:")
print(
    test_df[TARGET_COLUMN]
    .value_counts()
    .sort_index()
    .to_string()
)


# ------------------------------------------------------------
# CHECK ALL CLASSES EXIST IN EACH SPLIT
# ------------------------------------------------------------

all_classes = set(y.unique())

train_classes = set(y_train.unique())
val_classes = set(y_val.unique())
test_classes = set(y_test.unique())


print("\nClass coverage:")

print(
    "Training   :",
    sorted(train_classes)
)

print(
    "Validation :",
    sorted(val_classes)
)

print(
    "Testing    :",
    sorted(test_classes)
)


if train_classes != all_classes:
    raise ValueError(
        "Training set does not contain all fault classes."
    )

if val_classes != all_classes:
    raise ValueError(
        "Validation set does not contain all fault classes."
    )

if test_classes != all_classes:
    raise ValueError(
        "Test set does not contain all fault classes."
    )


# ------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("DATASET PREPARATION COMPLETE")
print("=" * 70)

print("\nFeatures used:")

for feature in FEATURE_COLUMNS:
    print(f"  - {feature}")

print("\nTarget:")
print(f"  - {TARGET_COLUMN}")

print("\nExcluded from ML:")
print("  - A")
print("  - B")
print("  - C")
print("  - G")

print("\nSaved files:")

print(f"  - {clean_dataset_path}")
print(f"  - {train_path}")
print(f"  - {val_path}")
print(f"  - {test_path}")

print("\n" + "=" * 70)