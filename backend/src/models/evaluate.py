"""
Model evaluation module for EduSight.
Computes all required metrics. Never fabricates results.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import MODELS_DIR, REPORTS_DIR


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
) -> dict:
    """Compute all evaluation metrics. Returns dict of metric → value."""
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)

    metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "brier_score": round(float(brier_score_loss(y_true, y_prob)), 4),
        "specificity": round(float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0, 4),
        "sensitivity": round(float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0, 4),
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
        "confusion_matrix": cm.tolist(),
    }
    return metrics


def evaluate_and_print(y_true, y_pred, y_prob, label: str = ""):
    metrics = evaluate_predictions(y_true, y_pred, y_prob)
    print(f"\n{'─'*50}")
    print(f"Evaluation [{label}]")
    print(f"{'─'*50}")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1:        {metrics['f1']:.4f}")
    print(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")
    print(f"  PR-AUC:    {metrics['pr_auc']:.4f}")
    print(f"  Brier:     {metrics['brier_score']:.4f}")
    print(f"  Confusion Matrix:")
    print(f"    TP={metrics['tp']}  FP={metrics['fp']}")
    print(f"    FN={metrics['fn']}  TN={metrics['tn']}")
    return metrics


def generate_evaluation_report(all_results: list, save_path: Path = None):
    """Generate comprehensive evaluation report from list of result dicts."""
    df = pd.DataFrame(all_results)
    if save_path is None:
        save_path = REPORTS_DIR / "experiments" / "evaluation_report.csv"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(save_path, index=False)
    print(f"\nEvaluation report → {save_path}")
    return df
