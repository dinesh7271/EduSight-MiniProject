"""
Unit and integration tests for EduSight Recourse Engine.
Verifies constraint enforcement, immutability, and feasibility bounds.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import IMMUTABLE_FEATURES, PERMITTED_RANGES, WINDOW_ACTIONABLE
from src.recourse.action_plan import build_action_plan, format_action_plan_text
from src.recourse.constraints import (
    calculate_max_achievable_grade,
    get_actionable_features,
    validate_counterfactual,
)


def test_actionable_features_per_window():
    w4 = get_actionable_features("week4")
    w8 = get_actionable_features("week8")
    w12 = get_actionable_features("week12")

    # Temporal monotonicity of actionable features
    assert len(w4) <= len(w8) <= len(w12)
    assert "Curricular_units_1st_sem_grade" not in w4
    assert "Curricular_units_1st_sem_grade" in w8
    assert "Curricular_units_2nd_sem_grade" in w12


def test_immutable_features_cannot_be_varied():
    orig = {"Gender": 1.0, "Age_at_enrollment": 20.0, "Curricular_units_1st_sem_approved": 2.0}
    cf = {"Gender": 0.0, "Age_at_enrollment": 18.0, "Curricular_units_1st_sem_approved": 5.0}

    val = validate_counterfactual(orig, cf, "week12")
    assert not val["valid"]
    assert not val["feasible"]

    violation_types = [v["type"] for v in val["violations"]]
    assert "IMMUTABLE_FEATURE" in violation_types


def test_permitted_range_enforcement():
    orig = {"Curricular_units_1st_sem_grade": 10.0}
    # Exceeds maximum 20.0
    cf = {"Curricular_units_1st_sem_grade": 25.0}

    val = validate_counterfactual(orig, cf, "week12")
    assert not val["valid"]
    range_violations = [v for v in val["violations"] if v["type"] == "RANGE_VIOLATION"]
    assert len(range_violations) > 0


def test_max_achievable_grade_computation():
    # 4 units passed with 10.0 (sum=40). 2 units remain. Max possible on remaining = 2 * 20 = 40.
    # Total units = 6. Max achievable = (40 + 40) / 6 = 13.33
    max_grade = calculate_max_achievable_grade(
        current_grade_sum=40.0, current_units=4, remaining_units=2
    )
    assert max_grade == pytest.approx(13.33, abs=0.01)


def test_action_plan_builder():
    mock_cf = {
        "counterfactuals": [
            {
                "changes": [
                    {
                        "feature": "Curricular_units_1st_sem_approved",
                        "from": 2.0,
                        "to": 5.0,
                    },
                    {
                        "feature": "Tuition_fees_up_to_date",
                        "from": 0.0,
                        "to": 1.0,
                    },
                ]
            }
        ]
    }
    student_row = {"Curricular_units_1st_sem_approved": 2.0, "Tuition_fees_up_to_date": 0.0}
    steps = build_action_plan(mock_cf, student_row)

    assert len(steps) == 2
    assert steps[0]["priority"] == "high"
    text = format_action_plan_text(steps)
    assert "Recommended actions" in text
    assert "advisor" in text.lower()
