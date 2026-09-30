"""
Leakage Detection Module for EduSight.

MANDATORY PHASE: This module audits every feature for temporal leakage
and target leakage before any model training begins.

Leakage policy:
- Target column (G3 / Target) NEVER enters features.
- Week 4 window: no grades at all (only enrollment behaviour + background).
- Week 8 window: first semester grade allowed.
- Week 12 window: first and second semester grades allowed.
- Any post-outcome information is forbidden.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    ALWAYS_EXCLUDED,
    FEATURES_WEEK12,
    FEATURES_WEEK4,
    FEATURES_WEEK8,
    REPORTS_DIR,
    WINDOW_FEATURES,
)

# Per-feature leakage classification
FEATURE_LEAKAGE_MAP = {
    # Available at all windows (Week 4, 8, 12)
    "Marital_status": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Application_mode": {"available_from": "week4", "leakage_risk": "none", "reason": "Admission record."},
    "Application_order": {"available_from": "week4", "leakage_risk": "none", "reason": "Admission record."},
    "Course": {"available_from": "week4", "leakage_risk": "none", "reason": "Enrollment record."},
    "Daytime_evening_attendance": {"available_from": "week4", "leakage_risk": "none", "reason": "Registration record."},
    "Previous_qualification": {"available_from": "week4", "leakage_risk": "none", "reason": "Pre-enrollment record."},
    "Previous_qualification_grade": {"available_from": "week4", "leakage_risk": "none", "reason": "Pre-enrollment record."},
    "Nacionality": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Mothers_qualification": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Fathers_qualification": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Mothers_occupation": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Fathers_occupation": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Displaced": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Educational_special_needs": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Debtor": {"available_from": "week4", "leakage_risk": "low", "reason": "Financial status, may change; use at prediction point."},
    "Tuition_fees_up_to_date": {"available_from": "week4", "leakage_risk": "low", "reason": "Financial status at prediction point."},
    "Gender": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Scholarship_holder": {"available_from": "week4", "leakage_risk": "none", "reason": "Enrollment record."},
    "Age_at_enrollment": {"available_from": "week4", "leakage_risk": "none", "reason": "Known at enrollment."},
    "International": {"available_from": "week4", "leakage_risk": "none", "reason": "Background demographic."},
    "Curricular_units_1st_sem_credited": {"available_from": "week4", "leakage_risk": "none", "reason": "Enrollment data (credits recognised before semester)."},
    "Curricular_units_1st_sem_enrolled": {"available_from": "week4", "leakage_risk": "none", "reason": "Enrollment data."},
    "Curricular_units_1st_sem_evaluations": {"available_from": "week4", "leakage_risk": "low", "reason": "Number of evaluations done — partial at week 4."},
    "Curricular_units_1st_sem_approved": {"available_from": "week4", "leakage_risk": "low", "reason": "Approved units by prediction point (not final)."},
    "Curricular_units_1st_sem_without_evaluations": {"available_from": "week4", "leakage_risk": "low", "reason": "Units not yet evaluated."},
    "GDP": {"available_from": "week4", "leakage_risk": "none", "reason": "Macroeconomic — available at any time."},
    "Inflation_rate": {"available_from": "week4", "leakage_risk": "none", "reason": "Macroeconomic — available at any time."},
    "Unemployment_rate": {"available_from": "week4", "leakage_risk": "none", "reason": "Macroeconomic — available at any time."},
    # Available from Week 8 (after 1st semester exams)
    "Curricular_units_1st_sem_grade": {"available_from": "week8", "leakage_risk": "none", "reason": "Final 1st semester grade — only available after 1st semester ends."},
    # Available from Week 12 (after 2nd semester)
    "Curricular_units_2nd_sem_credited": {"available_from": "week12", "leakage_risk": "none", "reason": "2nd semester data."},
    "Curricular_units_2nd_sem_enrolled": {"available_from": "week12", "leakage_risk": "none", "reason": "2nd semester data."},
    "Curricular_units_2nd_sem_evaluations": {"available_from": "week12", "leakage_risk": "none", "reason": "2nd semester data."},
    "Curricular_units_2nd_sem_approved": {"available_from": "week12", "leakage_risk": "none", "reason": "2nd semester data."},
    "Curricular_units_2nd_sem_grade": {"available_from": "week12", "leakage_risk": "none", "reason": "Final 2nd semester grade."},
    "Curricular_units_2nd_sem_without_evaluations": {"available_from": "week12", "leakage_risk": "none", "reason": "2nd semester data."},
    # ALWAYS EXCLUDED (target leakage)
    "Target": {"available_from": "never", "leakage_risk": "critical", "reason": "This IS the target. Absolutely excluded."},
    "at_risk": {"available_from": "never", "leakage_risk": "critical", "reason": "Derived target. Absolutely excluded."},
}

WINDOW_ORDER = {"week4": 0, "week8": 1, "week12": 2, "never": 999}


def check_target_leakage(features: list, window: str) -> list:
    """Returns list of target-leakage violations in the feature set."""
    violations = []
    for f in features:
        if f in ALWAYS_EXCLUDED:
            violations.append({
                "feature": f,
                "window": window,
                "violation_type": "TARGET_LEAKAGE",
                "severity": "CRITICAL",
            })
    return violations


def check_temporal_leakage(features: list, window: str) -> list:
    """Returns list of temporal leakage violations in the feature set."""
    violations = []
    window_idx = WINDOW_ORDER.get(window, 999)
    for f in features:
        meta = FEATURE_LEAKAGE_MAP.get(f, {})
        available_from = meta.get("available_from", "week4")
        available_idx = WINDOW_ORDER.get(available_from, 0)
        if available_idx > window_idx:
            violations.append({
                "feature": f,
                "window": window,
                "violation_type": "TEMPORAL_LEAKAGE",
                "severity": "CRITICAL",
                "reason": f"Feature available from {available_from}, not at {window}.",
            })
    return violations


def run_leakage_audit() -> dict:
    """Full leakage audit across all windows. Raises on critical violations."""
    all_violations = []
    window_reports = {}

    for window, features in WINDOW_FEATURES.items():
        target_v = check_target_leakage(features, window)
        temporal_v = check_temporal_leakage(features, window)
        violations = target_v + temporal_v
        all_violations.extend(violations)
        window_reports[window] = {
            "features": features,
            "n_features": len(features),
            "violations": violations,
            "status": "PASS" if not violations else "FAIL",
        }

    report = {
        "total_violations": len(all_violations),
        "critical_violations": [v for v in all_violations if v["severity"] == "CRITICAL"],
        "windows": window_reports,
        "overall_status": "PASS" if not all_violations else "FAIL",
    }
    return report


def save_leakage_report(report: dict):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "LEAKAGE_AUDIT.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Leakage audit saved → {path}")

    # Also write human-readable markdown
    md_path = REPORTS_DIR / "LEAKAGE_AUDIT.md"
    lines = [
        "# EduSight — Leakage Audit Report\n\n",
        f"**Overall Status: {report['overall_status']}**\n\n",
        f"Total violations: {report['total_violations']}\n\n",
    ]
    for window, wr in report["windows"].items():
        lines.append(f"## Window: {window} — {wr['status']}\n")
        lines.append(f"Features: {wr['n_features']}\n\n")
        if wr["violations"]:
            for v in wr["violations"]:
                lines.append(f"- ❌ **{v['feature']}**: {v['violation_type']} ({v.get('reason', '')})\n")
        else:
            lines.append("✓ No violations.\n\n")
    with open(md_path, "w") as f:
        f.writelines(lines)
    print(f"Leakage audit markdown → {md_path}")


if __name__ == "__main__":
    report = run_leakage_audit()
    print(f"\nLeakage Audit: {report['overall_status']}")
    if report["critical_violations"]:
        print("⚠ CRITICAL VIOLATIONS:")
        for v in report["critical_violations"]:
            print(f"  - [{v['window']}] {v['feature']}: {v['violation_type']}")
    else:
        print("✓ No leakage violations found.")
    save_leakage_report(report)
    if report["overall_status"] == "FAIL":
        raise SystemExit("BLOCKED: Leakage detected. Fix before model training.")
