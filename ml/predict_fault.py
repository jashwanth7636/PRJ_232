import os
import joblib
import pandas as pd


# ============================================================
# PRJ_232 - FAULT PREDICTION USING TRAINED MODEL
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

MODEL_FILE = os.path.join(
    PROJECT_ROOT,
    "ml",
    "artifacts",
    "best_fault_model.joblib"
)

LABEL_ENCODER_FILE = os.path.join(
    PROJECT_ROOT,
    "ml",
    "artifacts",
    "label_encoder.joblib"
)


# ------------------------------------------------------------
# LOAD TRAINED MODEL
# ------------------------------------------------------------

print("=" * 60)
print("PRJ_232 - ELECTRICAL FAULT PREDICTION")
print("=" * 60)

print("\nLoading trained model...")

model = joblib.load(MODEL_FILE)

label_encoder = joblib.load(LABEL_ENCODER_FILE)

print("Model loaded successfully.")


# ------------------------------------------------------------
# GET INPUT VALUES
# ------------------------------------------------------------

print("\nEnter electrical measurements.")

Ia = float(input("Ia: "))
Ib = float(input("Ib: "))
Ic = float(input("Ic: "))

Va = float(input("Va: "))
Vb = float(input("Vb: "))
Vc = float(input("Vc: "))


# ------------------------------------------------------------
# CREATE INPUT DATAFRAME
# ------------------------------------------------------------

input_data = pd.DataFrame(
    [[Ia, Ib, Ic, Va, Vb, Vc]],
    columns=[
        "Ia",
        "Ib",
        "Ic",
        "Va",
        "Vb",
        "Vc"
    ]
)


# ------------------------------------------------------------
# PREDICT
# ------------------------------------------------------------

prediction = model.predict(input_data)

predicted_class = label_encoder.inverse_transform(
    prediction.astype(int)
)[0]


# ------------------------------------------------------------
# PREDICTION PROBABILITY
# ------------------------------------------------------------

probabilities = model.predict_proba(
    input_data
)[0]

class_probabilities = dict(
    zip(
        label_encoder.classes_,
        probabilities
    )
)


# ------------------------------------------------------------
# DISPLAY RESULT
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("PREDICTION RESULT")
print("=" * 60)

print(
    f"\nPredicted Fault Type: {predicted_class}"
)

print("\nPrediction probabilities:")

for fault, probability in class_probabilities.items():

    print(
        f"  {fault:6} : "
        f"{probability * 100:.2f}%"
    )

print("\n" + "=" * 60)