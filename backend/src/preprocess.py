"""
Preprocessing pipeline for EduSight.
Reads raw UCI 697 CSV → outputs three feature window CSVs + feature manifest.

STRICT RULES:
- Target column (Target) is NEVER included in feature files.
- G1/G2 analogue (1st_sem_grade) only in Week 8+ window.
- 2nd semester data only in Week 12 window.
- No data fabrication — only use columns that actually exist in the dataset.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import (
    ALWAYS_EXCLUDED,
    BINARY_TARGET,
    PROCESSED_DIR,
    UCI697_RISK_MAPPING,
    UCI697_TARGET_COL,
    WINDOW_FEATURES,
)


def load_and_clean(path: Path) -> pd.DataFrame:
    """Load UCI 697 CSV and apply minimal, documented cleaning."""
    df = pd.read_csv(path, sep=";")
    # Normalize column names
    df.columns = [
        c.strip().replace(" ", "_").replace("(", "").replace(")", "")
        for c in df.columns
    ]

    original_rows = len(df)

    # Remove exact duplicate rows (document count)
    n_dup = df.duplicated().sum()
    if n_dup > 0:
        print(f"  Removing {n_dup} exact duplicate rows.")
        df = df.drop_duplicates()

    print(f"  Cleaned: {len(df)} rows (removed {original_rows - len(df)} duplicates)")
    return df


def create_binary_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create binary 'at_risk' target from native Target column.

    Experimental mapping (documented):
        Dropout → at_risk = 1
        Enrolled → at_risk = 0
        Graduate → at_risk = 0

    NOTE: Enrolled students are assigned 0 for this experiment.
    This is an intentional design choice: we identify Dropout risk.
    """
    if UCI697_TARGET_COL not in df.columns:
        raise ValueError(f"Column '{UCI697_TARGET_COL}' not found in dataset.")

    df = df.copy()
    df[BINARY_TARGET] = df[UCI697_TARGET_COL].map(UCI697_RISK_MAPPING)

    unmapped = df[BINARY_TARGET].isnull().sum()
    if unmapped > 0:
        raise ValueError(
            f"Unmapped target values: {df[df[BINARY_TARGET].isnull()][UCI697_TARGET_COL].unique()}"
        )

    df[BINARY_TARGET] = df[BINARY_TARGET].astype(int)
    print(f"\n  Binary target distribution:")
    for val, count in df[BINARY_TARGET].value_counts().items():
        label = "at_risk" if val == 1 else "not_at_risk"
        print(f"    {label} ({val}): {count} ({count/len(df)*100:.1f}%)")

    return df


def build_window_datasets(df: pd.DataFrame) -> dict:
    """Build feature sets for each prediction window. Returns dict of DataFrames."""
    datasets = {}
    for window, features in WINDOW_FEATURES.items():
        # Verify all features exist
        missing = [f for f in features if f not in df.columns]
        if missing:
            raise ValueError(
                f"[{window}] Features not found in dataset: {missing}\n"
                "STOP: Do not fabricate missing features. Check column names."
            )

        # Verify target is excluded
        for excl in ALWAYS_EXCLUDED:
            if excl in features:
                raise ValueError(
                    f"[{window}] LEAKAGE: '{excl}' must not be in feature list."
                )

        df_window = df[features + [BINARY_TARGET]].copy()
        datasets[window] = df_window
        print(f"  Window {window}: {df_window.shape[0]} rows × {len(features)} features")

    return datasets


def save_window_datasets(datasets: dict, manifest_path: Path = None) -> dict:
    """Save each window dataset to CSV. Returns feature manifest."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}

    for window, df in datasets.items():
        out_path = PROCESSED_DIR / f"features_{window}.csv"
        df.to_csv(out_path, index=False)
        print(f"  Saved → {out_path}")

        features = [c for c in df.columns if c != BINARY_TARGET]
        manifest[window] = {
            "file": str(out_path),
            "n_rows": len(df),
            "n_features": len(features),
            "features": features,
            "target": BINARY_TARGET,
            "positive_class": 1,
            "positive_label": "at_risk",
            "note": "Binary target: Dropout→1, Enrolled/Graduate→0 (experimental mapping)",
        }

    if manifest_path is None:
        manifest_path = PROCESSED_DIR / "feature_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n  Feature manifest → {manifest_path}")
    return manifest


def run_preprocessing():
    """Full preprocessing pipeline."""
    from src.config import UCI697_RAW
    print("=" * 60)
    print("EduSight Preprocessing Pipeline")
    print("=" * 60)

    print("\n[1/4] Loading data...")
    df_raw = load_and_clean(UCI697_RAW)
    print(f"  Loaded {df_raw.shape[0]} rows × {df_raw.shape[1]} columns")

    print("\n[2/4] Creating binary target...")
    df = create_binary_target(df_raw)

    print("\n[3/4] Building prediction windows...")
    datasets = build_window_datasets(df)

    print("\n[4/4] Saving processed datasets...")
    manifest = save_window_datasets(datasets)

    print("\n✓ Preprocessing complete.")
    return manifest


if __name__ == "__main__":
    run_preprocessing()
