"""
Pydantic schemas for EduSight API.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    student_id: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: str = "STUDENT"
    student_id: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    student_id: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Student Input ─────────────────────────────────────────────────────────────

class StudentIn(BaseModel):
    """Feature input for prediction. All fields optional with defaults."""
    window: str = "week12"
    # Background features
    Marital_status: Optional[float] = 1.0
    Application_mode: Optional[float] = 1.0
    Application_order: Optional[float] = 1.0
    Course: Optional[float] = 33.0
    Daytime_evening_attendance: Optional[float] = 1.0
    Previous_qualification: Optional[float] = 1.0
    Previous_qualification_grade: Optional[float] = 122.0
    Nacionality: Optional[float] = 1.0
    Mothers_qualification: Optional[float] = 2.0
    Fathers_qualification: Optional[float] = 2.0
    Mothers_occupation: Optional[float] = 10.0
    Fathers_occupation: Optional[float] = 10.0
    Displaced: Optional[float] = 0.0
    Educational_special_needs: Optional[float] = 0.0
    Debtor: Optional[float] = 0.0
    Tuition_fees_up_to_date: Optional[float] = 1.0
    Gender: Optional[float] = 1.0
    Scholarship_holder: Optional[float] = 0.0
    Age_at_enrollment: Optional[float] = 20.0
    International: Optional[float] = 0.0
    # 1st semester
    Curricular_units_1st_sem_credited: Optional[float] = 0.0
    Curricular_units_1st_sem_enrolled: Optional[float] = 6.0
    Curricular_units_1st_sem_evaluations: Optional[float] = 6.0
    Curricular_units_1st_sem_approved: Optional[float] = 5.0
    Curricular_units_1st_sem_grade: Optional[float] = 12.0
    Curricular_units_1st_sem_without_evaluations: Optional[float] = 0.0
    # 2nd semester (week12 only)
    Curricular_units_2nd_sem_credited: Optional[float] = 0.0
    Curricular_units_2nd_sem_enrolled: Optional[float] = 6.0
    Curricular_units_2nd_sem_evaluations: Optional[float] = 6.0
    Curricular_units_2nd_sem_approved: Optional[float] = 5.0
    Curricular_units_2nd_sem_grade: Optional[float] = 12.0
    Curricular_units_2nd_sem_without_evaluations: Optional[float] = 0.0
    # Macroeconomic
    GDP: Optional[float] = 1.74
    Inflation_rate: Optional[float] = 1.4
    Unemployment_rate: Optional[float] = 10.8


# ─── Predictions ──────────────────────────────────────────────────────────────

class PredictionOut(BaseModel):
    student_id: str
    risk_probability: float
    risk_level: str  # low, medium, high
    model_version: str
    threshold_version: str
    prediction_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Explanations ─────────────────────────────────────────────────────────────

class ExplanationItem(BaseModel):
    feature: str
    feature_label: str
    value: Optional[float] = None
    shap_value: float
    direction: str   # increases_risk or decreases_risk
    abs_shap: float

class ExplanationOut(BaseModel):
    student_id: str
    contributions: List[ExplanationItem]
    top_factors: List[ExplanationItem]
    explanation_text: str


# ─── Recourse ─────────────────────────────────────────────────────────────────

class ActionStep(BaseModel):
    feature: str
    feature_label: str
    current_value: float
    target_value: float
    change_amount: float
    priority: str   # high, medium, low
    feasible: bool
    note: Optional[str] = ""

class ActionPlanOut(BaseModel):
    student_id: str
    steps: List[ActionStep]
    plan_text: str
    generated_at: datetime


# ─── Cohort ───────────────────────────────────────────────────────────────────

class CohortSummary(BaseModel):
    total_students: int
    low_risk: int
    medium_risk: int
    high_risk: int
    latest_prediction_date: Optional[str] = None


# ─── Interventions ─────────────────────────────────────────────────────────────

class InterventionIn(BaseModel):
    student_id: str
    action_taken: str
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None

class InterventionOut(BaseModel):
    id: int
    student_id: str
    faculty_id: int
    action_taken: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Models ───────────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    model_version: str
    window: str
    training_date: Optional[str] = None
    dataset_id: str
    threshold: Optional[float] = None
    available: bool


class PredictRequest(BaseModel):
    student_id: str
    features: StudentIn
