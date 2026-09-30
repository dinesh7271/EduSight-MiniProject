"""
Counterfactual recourse constraints for EduSight.

Defines which features are immutable, actionable, or conditionally actionable.
Provides feasibility calculations for recommendations.

RULE: Counterfactuals CANNOT modify immutable features.
RULE: Recommended targets must be mathematically achievable.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import IMMUTABLE_FEATURES, PERMITTED_RANGES


def get_actionable_features(window: str) -> list:
    """Return list of actionable features for a given prediction window."""
    from src.config import WINDOW_ACTIONABLE
    return WINDOW_ACTIONABLE.get(window, [])


def validate_counterfactual(original: dict, counterfactual: dict, window: str) -> dict:
    """
    Validate a proposed counterfactual against all constraints.
    Returns dict: {valid, violations, feasible_changes}
    """
    violations = []
    feasible_changes = []
    actionable = set(get_actionable_features(window))

    for feat, new_val in counterfactual.items():
        orig_val = original.get(feat)
        if new_val == orig_val:
            continue

        # Immutable check
        if feat in IMMUTABLE_FEATURES:
            violations.append({
                "feature": feat,
                "type": "IMMUTABLE_FEATURE",
                "severity": "CRITICAL",
                "message": f"Feature '{feat}' is immutable and cannot be changed.",
            })
            continue

        # Actionability check
        if feat not in actionable:
            violations.append({
                "feature": feat,
                "type": "NON_ACTIONABLE",
                "severity": "WARNING",
                "message": f"Feature '{feat}' is not designated as actionable.",
            })
            continue

        # Range check
        allowed = PERMITTED_RANGES.get(feat)
        if allowed:
            lo, hi = allowed
            if not (lo <= new_val <= hi):
                violations.append({
                    "feature": feat,
                    "type": "RANGE_VIOLATION",
                    "severity": "ERROR",
                    "message": f"'{feat}' value {new_val} outside permitted range [{lo}, {hi}].",
                })
                continue

        feasible_changes.append({
            "feature": feat,
            "from": orig_val,
            "to": new_val,
        })

    critical = [v for v in violations if v["severity"] == "CRITICAL"]
    return {
        "valid": len(violations) == 0,
        "feasible": len(critical) == 0,
        "violations": violations,
        "feasible_changes": feasible_changes,
    }


def calculate_max_achievable_grade(
    current_grade_sum: float,
    current_units: int,
    remaining_units: int,
    max_grade_per_unit: float = 20.0,
) -> float:
    """
    Calculate maximum achievable average grade given remaining curriculum.
    Prevents recommending impossible grade targets.
    """
    max_future = remaining_units * max_grade_per_unit
    total_units = current_units + remaining_units
    if total_units == 0:
        return 0.0
    max_achievable = (current_grade_sum + max_future) / total_units
    return round(min(max_achievable, 20.0), 2)
