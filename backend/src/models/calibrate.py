"""
Probability calibration module for EduSight.
Calibrates model probabilities so risk = 0.80 means ~80% empirical risk.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import brier_score_loss

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import MODELS_DIR, RANDOM_SEED


def calibrate_model(pipe, X_train, y_train, method: str = "isotonic"):
    """
    Wrap a fitted pipeline with probability calibration.
    method: 'isotonic' or 'sigmoid' (Platt scaling).
    """
    calibrated = CalibratedClassifierCV(
        pipe, cv="prefit", method=method
    )
    calibrated.fit(X_train, y_train)
    return calibrated


def evaluate_calibration(y_true, y_prob, n_bins: int = 10) -> dict:
    """Compute calibration metrics."""
    fraction_of_positives, mean_predicted = calibration_curve(
        y_true, y_prob, n_bins=n_bins, strategy="uniform"
    )
    ece = float(np.mean(np.abs(fraction_of_positives - mean_predicted)))
    brier = float(brier_score_loss(y_true, y_prob))
    return {
        "expected_calibration_error": round(ece, 4),
        "brier_score": round(brier, 4),
        "fraction_of_positives": fraction_of_positives.tolist(),
        "mean_predicted_value": mean_predicted.tolist(),
    }


def save_calibrated_model(calibrated_model, window: str):
    path = MODELS_DIR / f"model_{window}_calibrated.joblib"
    joblib.dump(calibrated_model, path)
    print(f"Calibrated model → {path}")
    return path


if __name__ == "__main__":
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from src.config import BINARY_TARGET, PROCESSED_DIR

    for window in ["week4", "week8", "week12"]:
        df = pd.read_csv(PROCESSED_DIR / f"features_{window}.csv")
        X = df.drop(columns=[BINARY_TARGET])
        y = df[BINARY_TARGET]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
        )

        model_path = MODELS_DIR / f"model_{window}.joblib"
        if not model_path.exists():
            print(f"  ⚠ No model for {window}. Run train.py first.")
            continue

        pipe = joblib.load(model_path)
        print(f"\nCalibrating {window}...")

        calibrated = calibrate_model(pipe, X_train, y_train, method="isotonic")
        save_calibrated_model(calibrated, window)

        cal_probs = calibrated.predict_proba(X_test)[:, 1]
        cal_metrics = evaluate_calibration(y_test, cal_probs)
        print(f"  ECE: {cal_metrics['expected_calibration_error']:.4f}")
        print(f"  Brier: {cal_metrics['brier_score']:.4f}")
