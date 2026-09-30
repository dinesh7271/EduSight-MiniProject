"""
Data validation module for EduSight.
Audits raw datasets for quality issues before ML processing.

RULE: Report findings. Never modify raw data.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import REPORTS_DIR, UCI697_RAW


def load_uci697() -> pd.DataFrame:
    """Load UCI 697 dataset from raw CSV (semicolon-separated)."""
    if not UCI697_RAW.exists():
        raise FileNotFoundError(
            f"Dataset not found at {UCI697_RAW}. Run src/data/ingestion.py first."
        )
    df = pd.read_csv(UCI697_RAW, sep=";")
    # Normalize column names (strip spaces, replace spaces with underscores)
    df.columns = [c.strip().replace(" ", "_").replace("(", "").replace(")", "") for c in df.columns]
    return df


def run_audit(df: pd.DataFrame, dataset_name: str = "UCI-697") -> dict:
    """Perform full data quality audit. Returns structured report dict."""
    report = {}
    report["dataset"] = dataset_name
    report["shape"] = {"rows": int(df.shape[0]), "columns": int(df.shape[1])}
    report["columns"] = list(df.columns)
    report["dtypes"] = {c: str(df[c].dtype) for c in df.columns}

    # Missing values
    missing = df.isnull().sum()
    report["missing_values"] = {
        c: int(v) for c, v in missing.items() if v > 0
    }
    report["missing_pct"] = {
        c: round(float(v / len(df) * 100), 2) for c, v in missing.items() if v > 0
    }
    report["total_missing_cells"] = int(df.isnull().sum().sum())

    # Duplicate rows
    n_dup = int(df.duplicated().sum())
    report["duplicate_rows"] = n_dup

    # Target distribution
    if "Target" in df.columns:
        target_dist = df["Target"].value_counts().to_dict()
        report["target_distribution"] = {str(k): int(v) for k, v in target_dist.items()}
        report["class_imbalance_ratio"] = round(
            float(df["Target"].value_counts().max() / df["Target"].value_counts().min()), 2
        )

    # Numeric column stats
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    stats = {}
    for c in num_cols:
        stats[c] = {
            "min": float(df[c].min()),
            "max": float(df[c].max()),
            "mean": round(float(df[c].mean()), 4),
            "std": round(float(df[c].std()), 4),
            "n_unique": int(df[c].nunique()),
        }
    report["numeric_stats"] = stats

    # Categorical columns
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    report["categorical_columns"] = cat_cols
    for c in cat_cols:
        report[f"unique_{c}"] = df[c].unique().tolist()

    # Impossible / outlier values (numeric beyond domain)
    impossible = {}
    grade_cols = [c for c in num_cols if "grade" in c.lower() or "Grade" in c]
    for c in grade_cols:
        if df[c].max() > 20 or df[c].min() < 0:
            impossible[c] = {"min": float(df[c].min()), "max": float(df[c].max())}
    report["impossible_values"] = impossible

    # Potential leakage columns (to be confirmed by leakage.py)
    potential_leakage = []
    for c in df.columns:
        if any(kw in c.lower() for kw in ["final", "result", "outcome", "pass", "fail"]):
            potential_leakage.append(c)
    # Target itself is always leakage if used as feature
    if "Target" in df.columns:
        potential_leakage.append("Target")
    report["potential_leakage_columns"] = list(set(potential_leakage))

    return report


def save_audit_report(report: dict, name: str = "data_audit_report"):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{name}.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Audit report saved → {out_path}")
    return out_path


def print_audit_summary(report: dict):
    print("=" * 60)
    print(f"DATASET AUDIT: {report['dataset']}")
    print("=" * 60)
    print(f"Rows: {report['shape']['rows']}")
    print(f"Columns: {report['shape']['columns']}")
    print(f"Duplicate rows: {report['duplicate_rows']}")
    print(f"Total missing cells: {report['total_missing_cells']}")
    if report.get("target_distribution"):
        print(f"\nTarget distribution:")
        for cls, count in report["target_distribution"].items():
            pct = count / report["shape"]["rows"] * 100
            print(f"  {cls}: {count} ({pct:.1f}%)")
        print(f"  Imbalance ratio: {report['class_imbalance_ratio']:.2f}x")
    if report.get("impossible_values"):
        print(f"\n⚠ Impossible values found in: {list(report['impossible_values'].keys())}")
    if report.get("potential_leakage_columns"):
        print(f"\n⚠ Potential leakage columns: {report['potential_leakage_columns']}")
    print("=" * 60)


if __name__ == "__main__":
    print("Loading UCI 697...")
    df = load_uci697()
    print(f"Loaded: {df.shape[0]} rows × {df.shape[1]} columns")

    report = run_audit(df, "UCI-697")
    print_audit_summary(report)
    save_audit_report(report)
    print("\n✓ Data audit complete.")
