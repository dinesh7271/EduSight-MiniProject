"""
EduSight Configuration — Single Source of Truth
All feature lists, paths, constants, and target definitions live here.

Column names match the actual UCI 697 dataset after minimal normalization
(strip whitespace, replace spaces with underscores).
"""
from pathlib import Path

# ─── Project Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"

UCI697_RAW = RAW_DIR / "uci697" / "data.csv"
OULAD_RAW = RAW_DIR / "oulad"

# ─── Random State ─────────────────────────────────────────────────────────────
RANDOM_SEED = 42

# ─── Target Definition (UCI 697) ──────────────────────────────────────────────
# Native target: Dropout / Enrolled / Graduate (3-class)
# Experimental binary mapping (documented):
#   Dropout → at_risk = 1
#   Enrolled / Graduate → at_risk = 0
UCI697_TARGET_COL = "Target"
UCI697_RISK_MAPPING = {"Dropout": 1, "Enrolled": 0, "Graduate": 0}
BINARY_TARGET = "at_risk"

# ─── Leakage Policy ───────────────────────────────────────────────────────────
ALWAYS_EXCLUDED = [UCI697_TARGET_COL, BINARY_TARGET]

# ─── Actual column names from UCI 697 (after normalization) ───────────────────
# Verified by reading actual CSV header 2026-09-30
UCI697_COLUMNS_NORMALIZED = [
    "Marital_status",
    "Application_mode",
    "Application_order",
    "Course",
    "Daytime/evening_attendance",
    "Previous_qualification",
    "Previous_qualification_grade",
    "Nacionality",
    "Mother's_qualification",
    "Father's_qualification",
    "Mother's_occupation",
    "Father's_occupation",
    "Admission_grade",
    "Displaced",
    "Educational_special_needs",
    "Debtor",
    "Tuition_fees_up_to_date",
    "Gender",
    "Scholarship_holder",
    "Age_at_enrollment",
    "International",
    "Curricular_units_1st_sem_credited",
    "Curricular_units_1st_sem_enrolled",
    "Curricular_units_1st_sem_evaluations",
    "Curricular_units_1st_sem_approved",
    "Curricular_units_1st_sem_grade",
    "Curricular_units_1st_sem_without_evaluations",
    "Curricular_units_2nd_sem_credited",
    "Curricular_units_2nd_sem_enrolled",
    "Curricular_units_2nd_sem_evaluations",
    "Curricular_units_2nd_sem_approved",
    "Curricular_units_2nd_sem_grade",
    "Curricular_units_2nd_sem_without_evaluations",
    "Unemployment_rate",
    "Inflation_rate",
    "GDP",
]

# ─── Immutable Features ────────────────────────────────────────────────────────
IMMUTABLE_FEATURES = [
    "Marital_status",
    "Application_mode",
    "Application_order",
    "Course",
    "Daytime/evening_attendance",
    "Previous_qualification",
    "Previous_qualification_grade",
    "Admission_grade",
    "Nacionality",
    "Mother's_qualification",
    "Father's_qualification",
    "Mother's_occupation",
    "Father's_occupation",
    "Gender",
    "Age_at_enrollment",
    "International",
    "Educational_special_needs",
    "Displaced",
    "Scholarship_holder",
    "GDP",
    "Inflation_rate",
    "Unemployment_rate",
]

# ─── Actionable Features ──────────────────────────────────────────────────────
ACTIONABLE_FEATURES_W4 = [
    "Curricular_units_1st_sem_credited",
    "Curricular_units_1st_sem_enrolled",
    "Curricular_units_1st_sem_evaluations",
    "Curricular_units_1st_sem_approved",
    "Curricular_units_1st_sem_without_evaluations",
    "Debtor",
    "Tuition_fees_up_to_date",
]

ACTIONABLE_FEATURES_W8 = ACTIONABLE_FEATURES_W4 + [
    "Curricular_units_1st_sem_grade",
]

ACTIONABLE_FEATURES_W12 = ACTIONABLE_FEATURES_W8 + [
    "Curricular_units_2nd_sem_credited",
    "Curricular_units_2nd_sem_enrolled",
    "Curricular_units_2nd_sem_evaluations",
    "Curricular_units_2nd_sem_approved",
    "Curricular_units_2nd_sem_grade",
    "Curricular_units_2nd_sem_without_evaluations",
]

# ─── Feature Windows ──────────────────────────────────────────────────────────
# WEEK 4: background + 1st semester enrollment behavior (no grades)
FEATURES_WEEK4 = [
    "Marital_status",
    "Application_mode",
    "Application_order",
    "Course",
    "Daytime/evening_attendance",
    "Previous_qualification",
    "Previous_qualification_grade",
    "Admission_grade",
    "Nacionality",
    "Mother's_qualification",
    "Father's_qualification",
    "Mother's_occupation",
    "Father's_occupation",
    "Displaced",
    "Educational_special_needs",
    "Debtor",
    "Tuition_fees_up_to_date",
    "Gender",
    "Scholarship_holder",
    "Age_at_enrollment",
    "International",
    "Curricular_units_1st_sem_credited",
    "Curricular_units_1st_sem_enrolled",
    "Curricular_units_1st_sem_evaluations",
    "Curricular_units_1st_sem_approved",
    "Curricular_units_1st_sem_without_evaluations",
    "GDP",
    "Inflation_rate",
    "Unemployment_rate",
]

# WEEK 8: + 1st semester grade (after first internal assessment)
FEATURES_WEEK8 = FEATURES_WEEK4 + [
    "Curricular_units_1st_sem_grade",
]

# WEEK 12: + 2nd semester data (after second internal)
FEATURES_WEEK12 = FEATURES_WEEK8 + [
    "Curricular_units_2nd_sem_credited",
    "Curricular_units_2nd_sem_enrolled",
    "Curricular_units_2nd_sem_evaluations",
    "Curricular_units_2nd_sem_approved",
    "Curricular_units_2nd_sem_grade",
    "Curricular_units_2nd_sem_without_evaluations",
]

WINDOW_FEATURES = {
    "week4": FEATURES_WEEK4,
    "week8": FEATURES_WEEK8,
    "week12": FEATURES_WEEK12,
}

WINDOW_ACTIONABLE = {
    "week4": ACTIONABLE_FEATURES_W4,
    "week8": ACTIONABLE_FEATURES_W8,
    "week12": ACTIONABLE_FEATURES_W12,
}

# ─── Permitted ranges for counterfactual recourse ─────────────────────────────
PERMITTED_RANGES = {
    "Curricular_units_1st_sem_credited": [0, 12],
    "Curricular_units_1st_sem_enrolled": [0, 12],
    "Curricular_units_1st_sem_evaluations": [0, 20],
    "Curricular_units_1st_sem_approved": [0, 12],
    "Curricular_units_1st_sem_grade": [0.0, 20.0],
    "Curricular_units_1st_sem_without_evaluations": [0, 12],
    "Curricular_units_2nd_sem_credited": [0, 12],
    "Curricular_units_2nd_sem_enrolled": [0, 12],
    "Curricular_units_2nd_sem_evaluations": [0, 20],
    "Curricular_units_2nd_sem_approved": [0, 12],
    "Curricular_units_2nd_sem_grade": [0.0, 20.0],
    "Curricular_units_2nd_sem_without_evaluations": [0, 12],
    "Debtor": [0, 1],
    "Tuition_fees_up_to_date": [0, 1],
}

# ─── Model Configuration ──────────────────────────────────────────────────────
CV_FOLDS = 5
N_ESTIMATORS_RF = 400
FN_COST_WEIGHT = 5  # Missing at-risk student is 5x worse than false alarm
FP_COST_WEIGHT = 1

# ─── Human-readable feature labels ────────────────────────────────────────────
FEATURE_LABELS = {
    "Curricular_units_1st_sem_grade": "Internal Assessment 1 (CIA 1 Marks)",
    "Curricular_units_2nd_sem_grade": "Internal Assessment 2 (CIA 2 Marks)",
    "Curricular_units_1st_sem_approved": "Subjects / Courses Cleared",
    "Curricular_units_1st_sem_evaluations": "Internal Tests & Assignments Submitted",
    "Curricular_units_1st_sem_enrolled": "Semester Subjects Registered",
    "Curricular_units_1st_sem_credited": "Exempted / Credited Units",
    "Curricular_units_1st_sem_without_evaluations": "Un-evaluated Subjects",
    "Curricular_units_2nd_sem_approved": "2nd Half Subjects Cleared",
    "Curricular_units_2nd_sem_evaluations": "Internal Lab / Practical Evaluations",
    "Curricular_units_2nd_sem_enrolled": "Total Subjects Registered",
    "Curricular_units_2nd_sem_without_evaluations": "Pending Lab Evaluations",
    "Tuition_fees_up_to_date": "Tuition Fee Clearance",
    "Debtor": "Has Standing Arrears / Backlog Fees",
    "Daytime/evening_attendance": "Attendance Shift (Day/Evening)",
    "Admission_grade": "Qualifying Entrance / Admission Score",
    "Previous_qualification_grade": "Previous Semester CGPA / Percentage",
    "Scholarship_holder": "Scholarship Beneficiary",
    "Age_at_enrollment": "Age at Enrollment",
    "Gender": "Gender",
    "Displaced": "Displaced / Commuting Student",
    "International": "International Student",
    "Unemployment_rate": "Regional Economic Factor",
    "Inflation_rate": "Inflation Rate",
    "GDP": "Economic Index",
    "Course": "Academic Program / Degree Major",
    "Application_mode": "Application Category",
    "Application_order": "Department Preference Order",
    "Marital_status": "Marital Status",
}

# ─── Risk threshold levels ────────────────────────────────────────────────────
RISK_LEVELS = {
    "low":    (0.0,  0.35),
    "medium": (0.35, 0.60),
    "high":   (0.60, 1.01),
}
