"""
Drift monitoring module for EduSight.
Monitors feature distributions and prediction drift over time.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import REPORTS_DIR


def compute_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """
    Population Stability Index (PSI).
    PSI < 0.1: No significant change
    PSI 0.1-0.25: Moderate change
    PSI > 0.25: Significant change
    """
    def _bucket(arr):
        arr = np.array(arr, dtype=float)
        quantiles = np.percentile(arr, np.linspace(0, 100, buckets + 1))
        quantiles = np.unique(quantiles)
        counts, _ = np.histogram(arr, bins=quantiles)
        pct = counts / len(arr)
        return np.clip(pct, 1e-6, None)

    exp_pct = _bucket(expected)
    act_pct = _bucket(actual)
    min_len = min(len(exp_pct), len(act_pct))
    exp_pct = exp_pct[:min_len]
    act_pct = act_pct[:min_len]
    psi = np.sum((exp_pct - act_pct) * np.log(exp_pct / act_pct))
    return round(float(psi), 4)


def compute_ks_test(reference: np.ndarray, current: np.ndarray) -> dict:
    """KS test for distribution shift."""
    ks_stat, p_value = stats.ks_2samp(reference, current)
    return {
        "ks_statistic": round(float(ks_stat), 4),
        "p_value": round(float(p_value), 4),
        "drift_detected": p_value < 0.05,
    }


def check_feature_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list,
) -> dict:
    """Check drift across all features. Returns per-feature drift report."""
    drift_report = {}
    for feat in features:
        if feat not in reference_df.columns or feat not in current_df.columns:
            continue
        ref = reference_df[feat].dropna().values
        cur = current_df[feat].dropna().values
        if len(ref) < 10 or len(cur) < 10:
            continue

        ks = compute_ks_test(ref, cur)
        psi = compute_psi(ref, cur)
        drift_report[feat] = {
            "ks_test": ks,
            "psi": psi,
            "psi_interpretation": (
                "none" if psi < 0.1
                else "moderate" if psi < 0.25
                else "significant"
            ),
        }

    drifted = [f for f, v in drift_report.items() if v["ks_test"]["drift_detected"]]
    return {
        "features_checked": len(drift_report),
        "features_with_drift": len(drifted),
        "drifted_features": drifted,
        "per_feature": drift_report,
    }


def check_prediction_drift(
    historical_probs: np.ndarray,
    current_probs: np.ndarray,
) -> dict:
    """Monitor shift in predicted risk probabilities."""
    ks = compute_ks_test(historical_probs, current_probs)
    hist_mean = float(np.mean(historical_probs))
    curr_mean = float(np.mean(current_probs))
    return {
        "historical_mean_risk": round(hist_mean, 4),
        "current_mean_risk": round(curr_mean, 4),
        "mean_shift": round(curr_mean - hist_mean, 4),
        "ks_test": ks,
        "alert": abs(curr_mean - hist_mean) > 0.1,
    }
