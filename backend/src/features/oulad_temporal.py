"""
OULAD Temporal Feature Engineering for EduSight.
Constructs strict time-cutoff feature sets (Week 4, 8, 12) from OULAD interaction logs and assessments.
Enforces zero lookahead: interactions and assessments occurring AFTER the cutoff are strictly excluded.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import BINARY_TARGET, OULAD_RAW, PROCESSED_DIR

# Days corresponding to temporal windows in OULAD
WINDOW_DAYS = {
    "week4": 28,
    "week8": 56,
    "week12": 84,
}

OULAD_TARGET_MAPPING = {
    "Withdrawn": 1,
    "Fail": 1,
    "Pass": 0,
    "Distinction": 0,
}


def load_oulad_tables(raw_dir: Path = OULAD_RAW) -> dict:
    """Load core OULAD tables required for temporal features."""
    tables = {}
    for name in ["studentInfo", "studentRegistration", "assessments", "studentAssessment"]:
        path = raw_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"Missing OULAD table: {path}. Run src.data.oulad_ingestion first."
            )
        tables[name] = pd.read_csv(path)
        print(f"  Loaded {name}: {tables[name].shape[0]} rows")
    return tables


def build_oulad_window_features(tables: dict, cutoff_day: int) -> pd.DataFrame:
    """
    Build temporal features with strict cutoff <= cutoff_day.
    Zero future leakage: any event where date > cutoff_day is dropped.
    """
    students = tables["studentInfo"].copy()
    assessments = tables["assessments"].copy()
    student_assessments = tables["studentAssessment"].copy()

    # Create binary target
    students[BINARY_TARGET] = students["final_result"].map(OULAD_TARGET_MAPPING)
    students = students.dropna(subset=[BINARY_TARGET])
    students[BINARY_TARGET] = students[BINARY_TARGET].astype(int)

    # Merge assessment metadata
    sa = student_assessments.merge(
        assessments[["id_assessment", "assessment_type", "date", "weight"]],
        on="id_assessment",
        how="inner",
    )

    # STRICT TEMPORAL FILTER: only submissions on or before cutoff_day
    sa_window = sa[sa["date_submitted"] <= cutoff_day].copy()

    # Aggregate assessment performance per student
    sa_agg = sa_window.groupby(["code_module", "code_presentation", "id_student"]).agg(
        assessments_submitted=("score", "count"),
        avg_assessment_score=("score", "mean"),
        max_assessment_score=("score", "max"),
        min_assessment_score=("score", "min"),
        assessments_weighted_score=("score", lambda x: np.sum(x * sa_window.loc[x.index, "weight"]) / (sa_window.loc[x.index, "weight"].sum() + 1e-6)),
    ).reset_index()

    # Merge back to student records
    merged = students.merge(
        sa_agg,
        on=["code_module", "code_presentation", "id_student"],
        how="left",
    )

    # Impute missing assessment stats for students with 0 submissions by cutoff
    merged["assessments_submitted"] = merged["assessments_submitted"].fillna(0)
    merged["avg_assessment_score"] = merged["avg_assessment_score"].fillna(0.0)
    merged["max_assessment_score"] = merged["max_assessment_score"].fillna(0.0)
    merged["min_assessment_score"] = merged["min_assessment_score"].fillna(0.0)
    merged["assessments_weighted_score"] = merged["assessments_weighted_score"].fillna(0.0)

    # Demographic & enrollment encoding
    cat_cols = ["gender", "region", "highest_education", "imd_band", "age_band", "disability"]
    for col in cat_cols:
        merged[col] = pd.Categorical(merged[col]).codes

    feature_cols = [
        "gender", "region", "highest_education", "imd_band", "age_band",
        "num_of_prev_attempts", "studied_credits", "disability",
        "assessments_submitted", "avg_assessment_score", "max_assessment_score",
        "min_assessment_score", "assessments_weighted_score",
    ]

    out_df = merged[feature_cols + [BINARY_TARGET]].copy()
    print(f"  Cutoff Day {cutoff_day}: {out_df.shape[0]} rows × {len(feature_cols)} features")
    return out_df


def process_all_oulad_windows():
    """Build and save Week 4, 8, 12 feature CSVs for OULAD."""
    print("=" * 60)
    print("Building OULAD Temporal Feature Windows")
    print("=" * 60)

    tables = load_oulad_tables()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {}
    for window_name, cutoff_day in WINDOW_DAYS.items():
        print(f"\nProcessing {window_name} (cutoff <= day {cutoff_day})...")
        df_win = build_oulad_window_features(tables, cutoff_day)

        out_path = PROCESSED_DIR / f"oulad_features_{window_name}.csv"
        df_win.to_csv(out_path, index=False)
        print(f"  Saved → {out_path}")

        features = [c for c in df_win.columns if c != BINARY_TARGET]
        manifest[window_name] = {
            "file": str(out_path),
            "cutoff_day": cutoff_day,
            "n_rows": len(df_win),
            "n_features": len(features),
            "features": features,
            "target": BINARY_TARGET,
            "positive_label": "at_risk (Withdrawn or Fail)",
        }

    manifest_path = PROCESSED_DIR / "oulad_feature_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n✓ OULAD manifest → {manifest_path}")
    return manifest


if __name__ == "__main__":
    if (OULAD_RAW / "studentInfo.csv").exists():
        process_all_oulad_windows()
    else:
        print(f"OULAD raw tables not found in {OULAD_RAW}. Run src.data.oulad_ingestion first.")
