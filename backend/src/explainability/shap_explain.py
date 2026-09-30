"""
SHAP Explainability module for EduSight.

LANGUAGE RULES (must be followed in all text generated from SHAP):
✓ "Feature X contributed to the predicted risk."
✓ "Attendance was an important factor in this prediction."
✗ "Low attendance caused the student to fail."
✗ "The student will definitely fail."
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import shap.explainers._tree as tree_mod

# XGBoost 3.0+ compat: base_score in UBJSON dump is formatted as '[5E-1]' instead of '0.5'
if hasattr(tree_mod, "decode_ubjson_buffer"):
    _orig_decode = tree_mod.decode_ubjson_buffer

    def _patched_decode(fd):
        jmodel = _orig_decode(fd)
        try:
            lmp = jmodel.get("learner", {}).get("learner_model_param", {})
            if "base_score" in lmp and isinstance(lmp["base_score"], str):
                lmp["base_score"] = lmp["base_score"].strip("[]")
        except Exception:
            pass
        return jmodel

    tree_mod.decode_ubjson_buffer = _patched_decode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import FEATURE_LABELS, MODELS_DIR, REPORTS_DIR


def load_model_and_explainer(window: str):
    """Load fitted model. Use calibrated if available."""
    cal_path = MODELS_DIR / f"model_{window}_calibrated.joblib"
    plain_path = MODELS_DIR / f"model_{window}.joblib"
    path = cal_path if cal_path.exists() else plain_path
    if not path.exists():
        raise FileNotFoundError(f"No model found for window '{window}'. Run train.py first.")
    return joblib.load(path)


def extract_pipeline_and_classifier(model):
    """Extract underlying pipeline and classifier from model (handling CalibratedClassifierCV)."""
    curr = model
    while hasattr(curr, "estimator") and curr.estimator is not None:
        curr = curr.estimator
    if hasattr(curr, "named_steps"):
        clf = curr.named_steps.get("clf", curr[-1])
        return curr, clf
    return model, curr


def build_tree_explainer(pipe, X_sample: pd.DataFrame):
    """Build SHAP TreeExplainer from the classifier inside the pipeline."""
    base_pipe, clf = extract_pipeline_and_classifier(pipe)
    try:
        if hasattr(base_pipe, "named_steps"):
            steps = list(base_pipe.named_steps.items())
            clf_step_idx = next(i for i, (n, _) in enumerate(steps) if n == "clf")
            transform_steps = steps[:clf_step_idx]

            X_transformed = X_sample.copy()
            for name, transform in transform_steps:
                if hasattr(transform, "transform"):
                    X_transformed = transform.transform(X_transformed)
        else:
            X_transformed = X_sample
    except Exception:
        X_transformed = X_sample

    explainer = shap.TreeExplainer(clf)
    return explainer, X_transformed


def get_global_shap_values(pipe, X: pd.DataFrame, n_samples: int = 200) -> dict:
    """
    Compute global SHAP values (feature importance across cohort).
    Returns dict: feature → mean |SHAP|
    """
    X_sample = X.sample(min(n_samples, len(X)), random_state=42)
    explainer, X_transformed = build_tree_explainer(pipe, X_sample)

    shap_values = explainer.shap_values(X_transformed)
    # For binary classification, shap_values may be [class0, class1]
    if isinstance(shap_values, list) and len(shap_values) == 2:
        shap_vals = shap_values[1]
    else:
        shap_vals = shap_values

    feature_names = X.columns.tolist()
    mean_abs = np.abs(shap_vals).mean(axis=0)
    importance = dict(zip(feature_names, mean_abs.tolist()))
    importance_sorted = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    return importance_sorted


def get_local_shap_values(pipe, student_row: pd.DataFrame, feature_names: list) -> list:
    """
    Compute SHAP values for a single student.
    Returns list of dicts: [{feature, value, shap_value, label, direction}]
    """
    explainer, X_transformed = build_tree_explainer(pipe, student_row)
    shap_values = explainer.shap_values(X_transformed)

    if isinstance(shap_values, list) and len(shap_values) == 2:
        sv = shap_values[1][0]
    else:
        sv = shap_values[0]

    original_vals = student_row.iloc[0].to_dict()
    results = []
    for i, feat in enumerate(feature_names):
        shap_val = float(sv[i]) if i < len(sv) else 0.0
        feat_val = original_vals.get(feat, None)
        direction = "increases_risk" if shap_val > 0 else "decreases_risk"
        results.append({
            "feature": feat,
            "feature_label": FEATURE_LABELS.get(feat, feat),
            "value": feat_val,
            "shap_value": round(shap_val, 4),
            "direction": direction,
            "abs_shap": abs(shap_val),
        })

    results.sort(key=lambda x: x["abs_shap"], reverse=True)
    return results


def generate_explanation_text(shap_contributions: list, top_n: int = 3) -> str:
    """
    Generate careful natural-language explanation from SHAP values.
    Language strictly follows EduSight explanation rules.
    """
    lines = []
    top = shap_contributions[:top_n]
    for item in top:
        label = item["feature_label"]
        direction = item["direction"]
        if direction == "increases_risk":
            lines.append(
                f"• {label} contributed to the elevated predicted risk score."
            )
        else:
            lines.append(
                f"• {label} was associated with a lower risk in this prediction."
            )
    return (
        "Based on this prediction model, the following factors were most influential:\n"
        + "\n".join(lines)
        + "\n\nNote: These are model-based associations, not causal relationships."
    )


def save_explainer(explainer, window: str):
    path = MODELS_DIR / f"explainer_{window}.joblib"
    joblib.dump(explainer, path)
    print(f"Explainer saved → {path}")
    return path


if __name__ == "__main__":
    for window in ["week4", "week8", "week12"]:
        print(f"\n--- SHAP for {window} ---")
        pipe = load_model_and_explainer(window)
        df = pd.read_csv(
            Path(__file__).parent.parent.parent / "data" / "processed" / f"features_{window}.csv"
        )
        from src.config import BINARY_TARGET
        X = df.drop(columns=[BINARY_TARGET])

        global_imp = get_global_shap_values(pipe, X)
        print("Top 5 global features:")
        for feat, val in list(global_imp.items())[:5]:
            print(f"  {feat}: {val:.4f}")

        local = get_local_shap_values(pipe, X.iloc[[0]], X.columns.tolist())
        print("\nLocal explanation (student 0):")
        for item in local[:5]:
            print(f"  {item['feature_label']}: shap={item['shap_value']:.4f} ({item['direction']})")
