"""
ML Training Pipeline for EduSight.

Trains: Dummy, Logistic Regression, Random Forest, XGBoost
Uses imblearn Pipeline so SMOTE is applied ONLY inside each CV fold.
Never applies SMOTE to the full dataset before splitting.
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    BINARY_TARGET,
    CV_FOLDS,
    FN_COST_WEIGHT,
    FP_COST_WEIGHT,
    MODELS_DIR,
    N_ESTIMATORS_RF,
    PROCESSED_DIR,
    RANDOM_SEED,
)


def load_window(window: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load feature matrix and target for a given window."""
    path = PROCESSED_DIR / f"features_{window}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Run src/preprocess.py first. Missing: {path}")
    df = pd.read_csv(path)
    X = df.drop(columns=[BINARY_TARGET])
    y = df[BINARY_TARGET]
    return X, y


def build_pipelines() -> dict:
    """Build all model pipelines. SMOTE inside Pipeline = no leakage."""
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    pipelines = {
        "dummy": ImbPipeline([
            ("clf", DummyClassifier(strategy="stratified", random_state=RANDOM_SEED)),
        ]),
        "logistic_regression": ImbPipeline([
            ("smote", SMOTE(random_state=RANDOM_SEED)),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=1000, random_state=RANDOM_SEED, class_weight="balanced"
            )),
        ]),
        "random_forest": ImbPipeline([
            ("smote", SMOTE(random_state=RANDOM_SEED)),
            ("clf", RandomForestClassifier(
                n_estimators=N_ESTIMATORS_RF,
                random_state=RANDOM_SEED,
                n_jobs=-1,
                class_weight="balanced",
            )),
        ]),
        "xgboost": ImbPipeline([
            ("smote", SMOTE(random_state=RANDOM_SEED)),
            ("clf", XGBClassifier(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=5,
                subsample=0.8,
                colsample_bytree=0.8,
                use_label_encoder=False,
                eval_metric="logloss",
                random_state=RANDOM_SEED,
                verbosity=0,
            )),
        ]),
    }
    return pipelines, cv


def select_threshold(probs: np.ndarray, y_true: np.ndarray) -> float:
    """
    Select decision threshold using weighted F-score.
    FN cost is weighted FN_COST_WEIGHT x FP cost.
    Missing an at-risk student is worse than a false alarm.
    """
    from sklearn.metrics import recall_score, precision_score
    best_threshold = 0.5
    best_score = -1.0

    for t in np.arange(0.1, 0.9, 0.01):
        preds = (probs >= t).astype(int)
        rec = recall_score(y_true, preds, zero_division=0)
        prec = precision_score(y_true, preds, zero_division=0)
        score = FN_COST_WEIGHT * rec + FP_COST_WEIGHT * prec
        if score > best_score:
            best_score = score
            best_threshold = float(round(t, 2))

    return best_threshold


def train_best_model(window: str, model_name: str = "xgboost") -> dict:
    """
    Full training run for the best model on a given window.
    1. Load data
    2. Train/test split (80/20, stratified) — test set untouched until final eval
    3. Cross-val on train set for threshold selection
    4. Fit final model on full train set
    5. Select threshold on CV val probabilities
    6. Save model artifact
    """
    print(f"\n{'='*60}")
    print(f"Training {model_name} on window: {window}")
    print("=" * 60)

    X, y = load_window(window)
    print(f"  Data: {X.shape[0]} rows × {X.shape[1]} features")
    print(f"  Class distribution: {dict(y.value_counts())}")

    # Train/test split — test set is held out, not used for threshold or tuning
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

    pipelines, cv = build_pipelines()
    pipe = pipelines[model_name]

    # Cross-val probabilities on train set for threshold selection
    print("  Running cross-validation for threshold selection...")
    cv_probs = cross_val_predict(
        pipe, X_train, y_train, cv=cv, method="predict_proba"
    )[:, 1]
    threshold = select_threshold(cv_probs, y_train)
    print(f"  Selected threshold: {threshold} (FN cost weight: {FN_COST_WEIGHT}x)")

    # Fit final model on full training data
    print("  Fitting final model on full training set...")
    pipe.fit(X_train, y_train)

    # Final evaluation on held-out test set (done once, only here)
    test_probs = pipe.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= threshold).astype(int)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f"model_{window}.joblib"
    joblib.dump(pipe, model_path)
    print(f"  Model saved → {model_path}")

    threshold_data = {
        "threshold": threshold,
        "window": window,
        "model": model_name,
        "fn_cost_weight": FN_COST_WEIGHT,
        "fp_cost_weight": FP_COST_WEIGHT,
        "random_seed": RANDOM_SEED,
        "note": "Threshold selected on CV validation probabilities, not on test set.",
    }
    th_path = MODELS_DIR / f"threshold_{window}.json"
    with open(th_path, "w") as f:
        json.dump(threshold_data, f, indent=2)

    return {
        "model_path": str(model_path),
        "threshold": threshold,
        "X_test": X_test,
        "y_test": y_test,
        "test_probs": test_probs,
        "test_preds": test_preds,
        "X_train": X_train,
        "y_train": y_train,
        "pipe": pipe,
        "window": window,
        "model_name": model_name,
    }


def train_all_models_all_windows() -> dict:
    """Train all model types × all windows and save CV results."""
    from src.models.evaluate import evaluate_predictions

    pipelines, cv = build_pipelines()
    all_results = []

    for window in ["week4", "week8", "week12"]:
        X, y = load_window(window)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
        )

        for model_name, pipe in pipelines.items():
            print(f"\nTraining {model_name} @ {window}...")
            try:
                if model_name == "dummy":
                    pipe.fit(X_train, y_train)
                    probs = pipe.predict_proba(X_test)[:, 1]
                else:
                    pipe.fit(X_train, y_train)
                    probs = pipe.predict_proba(X_test)[:, 1]

                # Load threshold (default 0.5 for comparison models)
                th_path = MODELS_DIR / f"threshold_{window}.json"
                if th_path.exists():
                    with open(th_path) as f:
                        th_data = json.load(f)
                    threshold = th_data.get("threshold", 0.5)
                else:
                    threshold = 0.5

                preds = (probs >= threshold).astype(int)
                metrics = evaluate_predictions(y_test, preds, probs)
                metrics["model"] = model_name
                metrics["window"] = window
                all_results.append(metrics)
                print(
                    f"  ROC-AUC={metrics['roc_auc']:.3f}  "
                    f"F1={metrics['f1']:.3f}  "
                    f"Recall={metrics['recall']:.3f}"
                )
            except Exception as e:
                print(f"  ⚠ {model_name} @ {window} failed: {e}")

    results_df = pd.DataFrame(all_results)
    out_path = MODELS_DIR.parent / "reports" / "experiments" / "model_comparison.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(out_path, index=False)
    print(f"\n  Results table → {out_path}")
    return all_results


if __name__ == "__main__":
    # 1. Train best model (XGBoost) on all windows
    for window in ["week4", "week8", "week12"]:
        result = train_best_model(window, model_name="xgboost")
        from src.models.evaluate import evaluate_and_print
        evaluate_and_print(result["y_test"], result["test_preds"], result["test_probs"], window)
