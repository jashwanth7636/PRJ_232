import os
import pandas as pd
import numpy as np


# ============================================================
# PRJ_232 - DATA ORDER / SIMILARITY CHECK
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "classData.csv"
)

FEATURES = [
    "Ia",
    "Ib",
    "Ic",
    "Va",
    "Vb",
    "Vc"
]


print("=" * 70)
print("PRJ_232 - DATA ORDER RELIABILITY CHECK")
print("=" * 70)


# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

df = pd.read_csv(DATA_FILE)

print("\nDataset loaded:")
print(f"Rows: {len(df)}")


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

    return "Unknown"


df["Fault_Type"] = df.apply(
    get_fault_label,
    axis=1
)


# ------------------------------------------------------------
# CHECK CONSECUTIVE ROW SIMILARITY
# ------------------------------------------------------------

features = df[FEATURES].values


differences = np.abs(
    features[1:] - features[:-1]
)

mean_difference = differences.mean(axis=1)

median_difference = np.median(mean_difference)

mean_difference_overall = mean_difference.mean()

print("\nConsecutive-row feature difference:")

print(
    f"Mean difference   : {mean_difference_overall:.6f}"
)

print(
    f"Median difference : {median_difference:.6f}"
)


# ------------------------------------------------------------
# CHECK DIFFERENCE AT FAULT TRANSITIONS
# ------------------------------------------------------------

transition_indices = []

for i in range(1, len(df)):

    if df.loc[i, "Fault_Type"] != df.loc[i - 1, "Fault_Type"]:

        transition_indices.append(i)


print("\nFault transitions found:")
print(len(transition_indices))


print("\nDifferences at fault transitions:")

for index in transition_indices:

    difference = mean_difference[index - 1]

    previous_fault = df.loc[
        index - 1,
        "Fault_Type"
    ]

    current_fault = df.loc[
        index,
        "Fault_Type"
    ]

    print(
        f"{previous_fault} -> {current_fault} : "
        f"{difference:.6f}"
    )


# ------------------------------------------------------------
# WITHIN-CLASS VS BETWEEN-CLASS TRANSITION
# ------------------------------------------------------------

within_class_differences = []

for i in range(1, len(df)):

    if (
        df.loc[i, "Fault_Type"]
        ==
        df.loc[i - 1, "Fault_Type"]
    ):

        within_class_differences.append(
            mean_difference[i - 1]
        )


transition_differences = []

for index in transition_indices:

    transition_differences.append(
        mean_difference[index - 1]
    )


print("\n" + "=" * 70)
print("SIMILARITY SUMMARY")
print("=" * 70)

print(
    "\nAverage difference between consecutive "
    "samples within the same fault class:"
)

print(
    f"{np.mean(within_class_differences):.6f}"
)

print(
    "\nAverage difference at fault-class transitions:"
)

print(
    f"{np.mean(transition_differences):.6f}"
)


# ------------------------------------------------------------
# CHECK VERY SIMILAR NEIGHBORS
# ------------------------------------------------------------

threshold = np.percentile(
    within_class_differences,
    25
)

very_similar_count = np.sum(
    np.array(within_class_differences)
    <= threshold
)

very_similar_percentage = (
    very_similar_count
    /
    len(within_class_differences)
    *
    100
)


print(
    "\nPercentage of within-class consecutive "
    "pairs with very small feature differences:"
)

print(
    f"{very_similar_percentage:.2f}%"
)


# ------------------------------------------------------------
# FINAL INFORMATION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("RELIABILITY CHECK COMPLETE")
print("=" * 70)

print(
    "\nThis check is descriptive only."
)

print(
    "It does not modify the dataset or trained models."
)

print(
    "\nUse these results to decide whether the "
    "random stratified split needs additional discussion."
)

print("\n" + "=" * 70)