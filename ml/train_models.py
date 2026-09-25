import os
import pandas as pd
import joblib

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

from xgboost import XGBClassifier


# ============================================================
# PRJ_232 - ML MODEL TRAINING
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

TRAIN_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "splits",
    "train.csv"
)

VALIDATION_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "splits",
    "validation.csv"
)

TEST_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "splits",
    "test.csv"
)

ARTIFACTS_DIR = os.path.join(
    PROJECT_ROOT,
    "ml",
    "artifacts"
)

RESULTS_DIR = os.path.join(
    PROJECT_ROOT,
    "evaluation",
    "results"
)

FIGURES_DIR = os.path.join(
    PROJECT_ROOT,
    "evaluation",
    "figures"
)


os.makedirs(ARTIFACTS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)


print("=" * 70)
print("PRJ_232 - MACHINE LEARNING MODEL TRAINING")
print("=" * 70)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading datasets...")

train_df = pd.read_csv(TRAIN_FILE)
val_df = pd.read_csv(VALIDATION_FILE)
test_df = pd.read_csv(TEST_FILE)

print("Datasets loaded successfully.")


# ============================================================
# FEATURES AND TARGET
# ============================================================

FEATURES = [
    "Ia",
    "Ib",
    "Ic",
    "Va",
    "Vb",
    "Vc"
]

TARGET = "Fault_Type"


X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_val = val_df[FEATURES]
y_val = val_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]


print("\nTraining samples   :", len(X_train))
print("Validation samples :", len(X_val))
print("Test samples       :", len(X_test))


# ============================================================
# ENCODE TARGET LABELS
# ============================================================

label_encoder = LabelEncoder()

y_train_encoded = label_encoder.fit_transform(y_train)
y_val_encoded = label_encoder.transform(y_val)
y_test_encoded = label_encoder.transform(y_test)

print("\nFault classes:")

for number, label in enumerate(label_encoder.classes_):
    print(f"  {number} -> {label}")


# Save label encoder
label_encoder_path = os.path.join(
    ARTIFACTS_DIR,
    "label_encoder.joblib"
)

joblib.dump(
    label_encoder,
    label_encoder_path
)


# ============================================================
# SCALE FEATURES FOR LOGISTIC REGRESSION
# ============================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)

X_val_scaled = scaler.transform(X_val)

X_test_scaled = scaler.transform(X_test)


scaler_path = os.path.join(
    ARTIFACTS_DIR,
    "scaler.joblib"
)

joblib.dump(
    scaler,
    scaler_path
)


# ============================================================
# CREATE MODELS
# ============================================================

models = {

    "Logistic Regression": LogisticRegression(
        max_iter=1000,
        random_state=42
    ),

    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    ),

    "XGBoost": XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="mlogloss",
        n_jobs=-1
    )
}


# ============================================================
# TRAIN MODELS
# ============================================================

results = []

trained_models = {}


for model_name, model in models.items():

    print("\n" + "=" * 70)
    print(f"TRAINING: {model_name}")
    print("=" * 70)

    # Logistic Regression uses scaled data
    if model_name == "Logistic Regression":

        model.fit(
            X_train_scaled,
            y_train_encoded
        )

        val_predictions = model.predict(
            X_val_scaled
        )

    else:

        model.fit(
            X_train,
            y_train_encoded
        )

        val_predictions = model.predict(
            X_val
        )

    trained_models[model_name] = model

    # --------------------------------------------------------
    # VALIDATION METRICS
    # --------------------------------------------------------

    accuracy = accuracy_score(
        y_val_encoded,
        val_predictions
    )

    precision = precision_score(
        y_val_encoded,
        val_predictions,
        average="weighted",
        zero_division=0
    )

    recall = recall_score(
        y_val_encoded,
        val_predictions,
        average="weighted",
        zero_division=0
    )

    f1 = f1_score(
        y_val_encoded,
        val_predictions,
        average="weighted",
        zero_division=0
    )

    print(f"\nValidation Accuracy  : {accuracy:.4f}")
    print(f"Validation Precision : {precision:.4f}")
    print(f"Validation Recall    : {recall:.4f}")
    print(f"Validation F1 Score  : {f1:.4f}")


    print("\nValidation Classification Report:")

    print(
        classification_report(
            y_val_encoded,
            val_predictions,
            target_names=label_encoder.classes_,
            zero_division=0
        )
    )


    results.append({
        "Model": model_name,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1_Score": f1
    })


# ============================================================
# VALIDATION RESULTS
# ============================================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="F1_Score",
    ascending=False
)


print("\n" + "=" * 70)
print("VALIDATION MODEL COMPARISON")
print("=" * 70)

print(
    results_df.to_string(index=False)
)


# ============================================================
# SELECT MODEL USING VALIDATION F1
# ============================================================

best_model_name = results_df.iloc[0]["Model"]

best_model = trained_models[best_model_name]

print("\nSelected model:")
print(best_model_name)

print(
    "\nSelection criterion: Highest validation F1 score"
)


# ============================================================
# FINAL TEST EVALUATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL TEST EVALUATION")
print("=" * 70)


if best_model_name == "Logistic Regression":

    test_predictions = best_model.predict(
        X_test_scaled
    )

else:

    test_predictions = best_model.predict(
        X_test
    )


test_accuracy = accuracy_score(
    y_test_encoded,
    test_predictions
)

test_precision = precision_score(
    y_test_encoded,
    test_predictions,
    average="weighted",
    zero_division=0
)

test_recall = recall_score(
    y_test_encoded,
    test_predictions,
    average="weighted",
    zero_division=0
)

test_f1 = f1_score(
    y_test_encoded,
    test_predictions,
    average="weighted",
    zero_division=0
)


print(f"\nTest Accuracy  : {test_accuracy:.4f}")
print(f"Test Precision : {test_precision:.4f}")
print(f"Test Recall    : {test_recall:.4f}")
print(f"Test F1 Score  : {test_f1:.4f}")


print("\nTest Classification Report:")

print(
    classification_report(
        y_test_encoded,
        test_predictions,
        target_names=label_encoder.classes_,
        zero_division=0
    )
)


# ============================================================
# SAVE RESULTS
# ============================================================

results_path = os.path.join(
    RESULTS_DIR,
    "model_comparison.csv"
)

results_df.to_csv(
    results_path,
    index=False
)


# ============================================================
# SAVE BEST MODEL
# ============================================================

best_model_path = os.path.join(
    ARTIFACTS_DIR,
    "best_fault_model.joblib"
)

joblib.dump(
    best_model,
    best_model_path
)


# ============================================================
# SAVE FINAL TEST RESULTS
# ============================================================

test_results = pd.DataFrame({
    "Metric": [
        "Accuracy",
        "Precision",
        "Recall",
        "F1 Score"
    ],
    "Value": [
        test_accuracy,
        test_precision,
        test_recall,
        test_f1
    ]
})


test_results_path = os.path.join(
    RESULTS_DIR,
    "final_test_results.csv"
)

test_results.to_csv(
    test_results_path,
    index=False
)


# ============================================================
# CONFUSION MATRIX DATA
# ============================================================

cm = confusion_matrix(
    y_test_encoded,
    test_predictions
)

cm_df = pd.DataFrame(
    cm,
    index=label_encoder.classes_,
    columns=label_encoder.classes_
)


cm_path = os.path.join(
    RESULTS_DIR,
    "confusion_matrix.csv"
)

cm_df.to_csv(cm_path)


# ============================================================
# FINAL OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("MODEL TRAINING COMPLETE")
print("=" * 70)

print("\nBest model:")
print(best_model_name)

print("\nSaved files:")

print(
    f"  - {best_model_path}"
)

print(
    f"  - {scaler_path}"
)

print(
    f"  - {label_encoder_path}"
)

print(
    f"  - {results_path}"
)

print(
    f"  - {test_results_path}"
)

print(
    f"  - {cm_path}"
)

print("\n" + "=" * 70)