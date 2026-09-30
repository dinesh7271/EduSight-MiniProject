"""
Action Plan Engine for EduSight.
Converts validated counterfactuals into structured, human-readable action plans.
"""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import FEATURE_LABELS, PERMITTED_RANGES


PRIORITY_MAP = {
    "Curricular_units_1st_sem_approved": "high",
    "Curricular_units_1st_sem_grade": "high",
    "Curricular_units_2nd_sem_approved": "high",
    "Curricular_units_2nd_sem_grade": "high",
    "Tuition_fees_up_to_date": "high",
    "Debtor": "medium",
    "Curricular_units_1st_sem_evaluations": "medium",
    "Curricular_units_2nd_sem_evaluations": "medium",
    "Curricular_units_1st_sem_enrolled": "low",
    "Curricular_units_2nd_sem_enrolled": "low",
}


def build_action_plan(counterfactual_result: dict, student_row: dict) -> list:
    """
    Convert counterfactual changes into structured action steps.

    Each step:
    {
        feature, feature_label, current_value, target_value,
        priority, feasible, note
    }
    """
    if not counterfactual_result.get("counterfactuals"):
        return []

    # Use first valid counterfactual
    best_cf = counterfactual_result["counterfactuals"][0]
    changes = best_cf.get("changes", [])

    steps = []
    for change in changes:
        feat = change["feature"]
        current = change["from"]
        target = change["to"]

        # Validate target is within permitted range
        allowed = PERMITTED_RANGES.get(feat)
        feasible = True
        note = ""
        if allowed:
            lo, hi = allowed
            if not (lo <= target <= hi):
                feasible = False
                note = f"Target {target} outside permitted range [{lo}, {hi}]. Capped."
                target = max(lo, min(hi, target))

        steps.append({
            "feature": feat,
            "feature_label": FEATURE_LABELS.get(feat, feat),
            "current_value": current,
            "target_value": round(float(target), 2),
            "change_amount": round(float(target) - float(current), 2),
            "priority": PRIORITY_MAP.get(feat, "medium"),
            "feasible": feasible,
            "note": note,
        })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    steps.sort(key=lambda x: priority_order.get(x["priority"], 1))
    return steps


def format_action_plan_text(steps: list) -> str:
    """Convert action steps to readable text."""
    if not steps:
        return "No specific actions could be generated. Please consult your academic advisor."

    lines = ["Recommended actions to reduce predicted risk:\n"]
    for i, step in enumerate(steps, 1):
        feasible_str = "" if step["feasible"] else " [Note: may require additional support]"
        lines.append(
            f"{i}. {step['feature_label']}: "
            f"current {step['current_value']} → target {step['target_value']} "
            f"({step['priority']} priority){feasible_str}"
        )

    lines.append(
        "\nThese are model-based suggestions. "
        "Please discuss with your faculty advisor before taking action."
    )
    return "\n".join(lines)
