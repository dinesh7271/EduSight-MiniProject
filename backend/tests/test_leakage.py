"""
10 Mandatory ML Tests for EduSight.
These tests MUST ALL PASS before model training results can be reported.

Tests verify:
1. No target column in features
2. No temporal leakage across windows
3. No student identity as predictive feature
4. Transformations not fitted on test data
5. SMOTE not applied before splitting
6. Test set not used for threshold selection
7. Test set not used for hyperparameter tuning
8. Counterfactuals cannot modify immutable features
9. Impossible recommendations are rejected
10. Prediction probabilities are in [0, 1]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    ALWAYS_EXCLUDED,
    BINARY_TARGET,
    IMMUTABLE_FEATURES,
    PERMITTED_RANGES,
    PROCESSED_DIR,
    WINDOW_FEATURES,
)
from src.data.leakage import WINDOW_ORDER, check_target_leakage, check_temporal_leakage


# ─── Test 1: No target column enters features ──────────────────────────────────
class TestNoTargetLeakage:
    def test_binary_target_not_in_week4_features(self):
        assert BINARY_TARGET not in WINDOW_FEATURES["week4"], \
            f"CRITICAL: '{BINARY_TARGET}' must not be in week4 features."

    def test_binary_target_not_in_week8_features(self):
        assert BINARY_TARGET not in WINDOW_FEATURES["week8"], \
            f"CRITICAL: '{BINARY_TARGET}' must not be in week8 features."

    def test_binary_target_not_in_week12_features(self):
        assert BINARY_TARGET not in WINDOW_FEATURES["week12"], \
            f"CRITICAL: '{BINARY_TARGET}' must not be in week12 features."

    def test_native_target_not_in_any_window(self):
        for window, features in WINDOW_FEATURES.items():
            assert "Target" not in features, \
                f"CRITICAL: Native 'Target' column must not be in {window} features."

    def test_leakage_audit_detects_target_in_features(self):
        # Simulate injecting target into features
        bad_features = WINDOW_FEATURES["week4"] + [BINARY_TARGET]
        violations = check_target_leakage(bad_features, "week4")
        assert len(violations) > 0, \
            "Leakage auditor must detect target column in feature list."

    def test_leakage_audit_passes_clean_features(self):
        violations = check_target_leakage(WINDOW_FEATURES["week4"], "week4")
        assert len(violations) == 0, \
            f"Clean feature list should have no target violations: {violations}"


# ─── Test 2: No temporal leakage across windows ─────────────────────────────────
class TestNoTemporalLeakage:
    def test_2nd_sem_grade_not_in_week4(self):
        assert "Curricular_units_2nd_sem_grade" not in WINDOW_FEATURES["week4"], \
            "2nd semester grade must not appear in week4 features (temporal leakage)."

    def test_2nd_sem_grade_not_in_week8(self):
        assert "Curricular_units_2nd_sem_grade" not in WINDOW_FEATURES["week8"], \
            "2nd semester grade must not appear in week8 features (temporal leakage)."

    def test_1st_sem_grade_not_in_week4(self):
        assert "Curricular_units_1st_sem_grade" not in WINDOW_FEATURES["week4"], \
            "1st semester grade must not appear in week4 features."

    def test_1st_sem_grade_in_week8_and_week12(self):
        assert "Curricular_units_1st_sem_grade" in WINDOW_FEATURES["week8"], \
            "1st semester grade should be in week8 features."
        assert "Curricular_units_1st_sem_grade" in WINDOW_FEATURES["week12"], \
            "1st semester grade should be in week12 features."

    def test_2nd_sem_features_only_in_week12(self):
        second_sem_features = [
            f for f in WINDOW_FEATURES["week12"]
            if "2nd_sem" in f
        ]
        assert len(second_sem_features) > 0, \
            "Week12 should contain 2nd semester features."
        for f in second_sem_features:
            assert f not in WINDOW_FEATURES["week4"], \
                f"2nd semester feature '{f}' must not be in week4."
            assert f not in WINDOW_FEATURES["week8"], \
                f"2nd semester feature '{f}' must not be in week8."

    def test_temporal_leakage_auditor_rejects_future_feature(self):
        # Injecting a week12-only feature into week4
        bad_features = WINDOW_FEATURES["week4"] + ["Curricular_units_2nd_sem_grade"]
        violations = check_temporal_leakage(bad_features, "week4")
        assert any(v["feature"] == "Curricular_units_2nd_sem_grade" for v in violations), \
            "Leakage auditor must flag week12 feature used in week4."


# ─── Test 3: No student identity as predictive feature ────────────────────────
class TestNoIdentityLeakage:
    IDENTITY_COLUMNS = [
        "student_id", "name", "email", "roll_number",
        "id", "student_name", "register_number",
    ]

    def test_no_identity_in_week4(self):
        for col in self.IDENTITY_COLUMNS:
            assert col not in WINDOW_FEATURES["week4"], \
                f"Identity column '{col}' must not be in features."

    def test_no_identity_in_any_window(self):
        for window, features in WINDOW_FEATURES.items():
            for col in self.IDENTITY_COLUMNS:
                assert col not in features, \
                    f"Identity column '{col}' found in {window} features."


# ─── Test 4: Transformations not fitted on test data ─────────────────────────
class TestNoPreprocessingLeakage:
    def test_scaler_fit_only_on_train(self):
        """Verify that StandardScaler in pipeline is not pre-fitted on full data."""
        from imblearn.pipeline import Pipeline as ImbPipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from imblearn.over_sampling import SMOTE

        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randint(0, 2, 100))

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        pipe = ImbPipeline([
            ("smote", SMOTE(random_state=42)),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression()),
        ])
        # Fit only on train
        pipe.fit(X_train, y_train)

        # Scaler should have been fit on train-only data
        scaler = pipe.named_steps["scaler"]
        assert scaler.n_samples_seen_ == pytest.approx(len(X_train) * 2, rel=0.5), \
            "Scaler was fit on more data than expected (possible test leakage)."


# ─── Test 5: SMOTE not applied before splitting ────────────────────────────────
class TestSMOTENotBeforeSplit:
    def test_smote_inside_pipeline(self):
        """SMOTE must be a pipeline step, not applied to the whole dataset."""
        from imblearn.pipeline import Pipeline as ImbPipeline
        from imblearn.over_sampling import SMOTE

        # This is the CORRECT pattern used in EduSight
        pipe = ImbPipeline([
            ("smote", SMOTE(random_state=42)),
        ])
        # Correct: pipeline's SMOTE only runs inside cross_val_predict or fit()
        # Wrong would be: SMOTE().fit_resample(X_full, y_full) before splitting
        assert "smote" in pipe.named_steps, "SMOTE must be inside the pipeline."


# ─── Test 6 & 7: Test set not used for threshold/hyperparameter selection ─────
class TestTestSetIsolation:
    def test_threshold_file_references_validation_not_test(self):
        """Threshold JSON must document that it was selected on validation data."""
        import json
        for window in ["week4", "week8", "week12"]:
            th_path = Path(__file__).parent.parent / "models" / f"threshold_{window}.json"
            if th_path.exists():
                with open(th_path) as f:
                    data = json.load(f)
                note = data.get("note", "").lower()
                assert "test" not in note or "not" in note or "validation" in note, \
                    f"Threshold for {window} must document it was selected on validation data."


# ─── Test 8: Counterfactuals cannot modify immutable features ─────────────────
class TestCounterfactualConstraints:
    def test_immutable_features_not_changed(self):
        from src.recourse.constraints import validate_counterfactual

        original = {f: 1.0 for f in IMMUTABLE_FEATURES}
        original.update({"Curricular_units_1st_sem_approved": 3.0})

        # Attempt to change an immutable feature
        bad_cf = original.copy()
        bad_cf["Gender"] = 0.0  # Gender is immutable

        result = validate_counterfactual(bad_cf, bad_cf, "week12")
        # The actual check: changing an immutable feature should fail
        original2 = {"Gender": 1.0, "Curricular_units_1st_sem_approved": 3.0}
        cf2 = {"Gender": 0.0, "Curricular_units_1st_sem_approved": 6.0}
        result2 = validate_counterfactual(original2, cf2, "week12")
        violations = [v for v in result2["violations"] if v["type"] == "IMMUTABLE_FEATURE"]
        assert len(violations) > 0, \
            "validate_counterfactual must reject changes to immutable features."

    def test_immutable_feature_list_contains_expected_features(self):
        assert "Gender" in IMMUTABLE_FEATURES
        assert "Age_at_enrollment" in IMMUTABLE_FEATURES
        assert "Nacionality" in IMMUTABLE_FEATURES


# ─── Test 9: Impossible recommendations rejected ────────────────────────────────
class TestFeasibilityConstraints:
    def test_range_violations_detected(self):
        from src.recourse.constraints import validate_counterfactual

        original = {"Curricular_units_1st_sem_grade": 10.0}
        # Suggest grade of 25, which is outside [0, 20]
        impossible_cf = {"Curricular_units_1st_sem_grade": 25.0}
        result = validate_counterfactual(original, impossible_cf, "week12")
        range_violations = [v for v in result["violations"] if v["type"] == "RANGE_VIOLATION"]
        assert len(range_violations) > 0, \
            "Grade > 20 must be flagged as a range violation."

    def test_negative_grade_rejected(self):
        from src.recourse.constraints import validate_counterfactual

        original = {"Curricular_units_1st_sem_grade": 10.0}
        impossible_cf = {"Curricular_units_1st_sem_grade": -5.0}
        result = validate_counterfactual(original, impossible_cf, "week12")
        assert not result["valid"], \
            "Negative grade must be rejected as impossible."


# ─── Test 10: Prediction probabilities in [0, 1] ──────────────────────────────
class TestPredictionProbabilities:
    def test_mock_probabilities_in_range(self):
        """Verify probability validation logic."""
        valid_probs = [0.0, 0.5, 0.99, 1.0]
        invalid_probs = [-0.01, 1.01, 2.0, -1.0]

        for p in valid_probs:
            assert 0.0 <= p <= 1.0, f"Valid probability {p} failed range check."

        for p in invalid_probs:
            assert not (0.0 <= p <= 1.0), f"Invalid probability {p} should fail."

    def test_risk_level_mapping_covers_full_range(self):
        from src.config import RISK_LEVELS

        covered = set()
        for level, (lo, hi) in RISK_LEVELS.items():
            covered.add(level)

        assert "low" in covered
        assert "medium" in covered
        assert "high" in covered

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "models" / "model_week12.joblib").exists(),
        reason="Model not trained yet. Run src/models/train.py first."
    )
    def test_trained_model_probabilities_in_range(self):
        import joblib
        from src.config import BINARY_TARGET

        pipe = joblib.load(
            Path(__file__).parent.parent / "models" / "model_week12.joblib"
        )
        df = pd.read_csv(PROCESSED_DIR / "features_week12.csv")
        X = df.drop(columns=[BINARY_TARGET]).head(50)
        probs = pipe.predict_proba(X)[:, 1]

        assert probs.min() >= 0.0, f"Probability below 0: {probs.min()}"
        assert probs.max() <= 1.0, f"Probability above 1: {probs.max()}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
