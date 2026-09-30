"""
EduSight FastAPI Application — Main entry point.

Loads ML models once at startup. Provides prediction, explanation,
recourse, cohort management, and authentication endpoints.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.api.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_student_access,
)
from src.api.db import AuditLog, Intervention, Prediction, User, create_tables, get_db
from src.api.schemas import (
    ActionPlanOut,
    ActionStep,
    CohortSummary,
    ExplanationItem,
    ExplanationOut,
    InterventionIn,
    InterventionOut,
    LoginRequest,
    ModelInfo,
    PredictRequest,
    PredictionOut,
    TokenResponse,
    UserCreate,
    UserOut,
)
from src.config import MODELS_DIR, RISK_LEVELS, WINDOW_FEATURES

app = FastAPI(
    title="EduSight API",
    description="AI-Powered Academic Early Warning System",
    version="1.0.0",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Model Store (loaded once at startup) ──────────────────────────────────────
class ModelStore:
    def __init__(self):
        self.models = {}
        self.thresholds = {}
        self.registries = {}

    def load(self):
        for window in ["week4", "week8", "week12"]:
            # Try calibrated first, then plain
            for suffix in ["_calibrated", ""]:
                path = MODELS_DIR / f"model_{window}{suffix}.joblib"
                if path.exists():
                    self.models[window] = joblib.load(path)
                    print(f"  Loaded model: {path.name}")
                    break

            th_path = MODELS_DIR / f"threshold_{window}.json"
            if th_path.exists():
                with open(th_path) as f:
                    self.thresholds[window] = json.load(f)

            reg_path = MODELS_DIR / f"registry_xgboost_{window}.json"
            if reg_path.exists():
                with open(reg_path) as f:
                    self.registries[window] = json.load(f)

    def get_model(self, window: str):
        model = self.models.get(window)
        if model is None:
            raise HTTPException(
                status_code=503,
                detail=f"Model for window '{window}' not loaded. Run train.py first.",
            )
        return model

    def get_threshold(self, window: str) -> float:
        th_data = self.thresholds.get(window, {})
        return th_data.get("threshold", 0.5)

    def get_version(self, window: str) -> str:
        reg = self.registries.get(window, {})
        return reg.get("model_version", f"model-{window}-unknown")


model_store = ModelStore()


# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    print("\nEduSight API starting up...")
    create_tables()

    # Load models
    print("Loading ML models...")
    model_store.load()
    if not model_store.models:
        print("  ⚠ No models loaded. Train models first using: python -m src.models.train")

    # Seed default users
    from src.api.db import SessionLocal
    db = SessionLocal()
    try:
        _seed_default_users(db)
    finally:
        db.close()
    print("✓ EduSight API ready.\n")


def _seed_default_users(db: Session):
    """Create default admin, faculty, and student accounts if not present."""
    defaults = [
        {"username": "admin", "password": "admin123", "role": "ADMIN", "email": "admin@edusight.local"},
        {"username": "faculty1", "password": "faculty123", "role": "FACULTY", "email": "faculty1@edusight.local"},
        {"username": "student1", "password": "student123", "role": "STUDENT",
         "email": "student1@edusight.local", "student_id": "student-001"},
        {"username": "student2", "password": "student123", "role": "STUDENT",
         "email": "student2@edusight.local", "student_id": "student-002"},
        {"username": "student3", "password": "student123", "role": "STUDENT",
         "email": "student3@edusight.local", "student_id": "student-003"},
    ]
    for d in defaults:
        exists = db.query(User).filter(User.username == d["username"]).first()
        if not exists:
            user = User(
                username=d["username"],
                email=d.get("email"),
                hashed_password=hash_password(d["password"]),
                role=d["role"],
                student_id=d.get("student_id"),
            )
            db.add(user)
    db.commit()
    print("  ✓ Default users seeded.")


def _get_risk_level(probability: float) -> str:
    for level, (lo, hi) in RISK_LEVELS.items():
        if lo <= probability < hi:
            return level
    return "high"


def _log_audit(db: Session, user: User, action: str, resource: str = None,
               resource_id: str = None, model_version: str = None):
    entry = AuditLog(
        user_id=user.id,
        username=user.username,
        action=action,
        resource=resource,
        resource_id=resource_id,
        model_version=model_version,
    )
    db.add(entry)
    db.commit()


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    loaded_windows = list(model_store.models.keys())
    return {
        "status": "ok",
        "models_loaded": loaded_windows,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─── Auth ─────────────────────────────────────────────────────────────────────
@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        student_id=user.student_id,
    )


@app.post("/api/auth/register", response_model=TokenResponse)
def register(req: UserCreate, db: Session = Depends(get_db)):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    clean_username = req.username.strip()
    if len(clean_username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long.")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(status_code=400, detail="Username already exists. Please choose another.")

    role = req.role.upper()
    if role not in ["STUDENT", "FACULTY", "ADMIN"]:
        role = "STUDENT"

    student_id = req.student_id
    if role == "STUDENT" and not student_id:
        count = db.query(User).filter(User.role == "STUDENT").count()
        student_id = f"student-{count + 1:03d}"

    user = User(
        username=clean_username,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=role,
        student_id=student_id if role == "STUDENT" else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        student_id=user.student_id,
    )


# ─── Students ─────────────────────────────────────────────────────────────────
@app.get("/api/students/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/api/students", response_model=List[UserOut])
def list_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("FACULTY", "ADMIN")),
):
    return db.query(User).filter(User.role == "STUDENT", User.is_active == True).all()


@app.get("/api/students/{student_id}", response_model=UserOut)
def get_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_student_access(current_user, student_id)
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found.")
    return user


# ─── Predictions ──────────────────────────────────────────────────────────────
@app.post("/api/predict", response_model=PredictionOut)
def predict(
    req: PredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_student_access(current_user, req.student_id)
    window = req.features.window

    pipe = model_store.get_model(window)
    threshold = model_store.get_threshold(window)
    model_version = model_store.get_version(window)

    # Build feature DataFrame using only features for this window
    feature_names = WINDOW_FEATURES[window]
    features_dict = req.features.model_dump(exclude={"window"})
    row_data = {f: features_dict.get(f, 0.0) for f in feature_names}
    student_df = pd.DataFrame([row_data])

    # Ensure correct dtype
    for col in student_df.columns:
        student_df[col] = pd.to_numeric(student_df[col], errors="coerce").fillna(0.0)

    prob = float(pipe.predict_proba(student_df)[0, 1])
    risk_level = _get_risk_level(prob)

    # Save to DB
    pred = Prediction(
        student_id=req.student_id,
        window=window,
        risk_probability=round(prob, 4),
        risk_level=risk_level,
        model_version=model_version,
        threshold_version=f"threshold-{window}-001",
        features_used=json.dumps(row_data),
        created_by=current_user.id,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)

    _log_audit(db, current_user, "PREDICT", "prediction", str(pred.id), model_version)

    return PredictionOut(
        student_id=req.student_id,
        risk_probability=round(prob, 4),
        risk_level=risk_level,
        model_version=model_version,
        threshold_version=f"threshold-{window}-001",
        prediction_id=pred.id,
        created_at=pred.created_at,
    )


@app.get("/api/predictions/{student_id}")
def get_predictions(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_student_access(current_user, student_id)
    preds = (
        db.query(Prediction)
        .filter(Prediction.student_id == student_id)
        .order_by(Prediction.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": p.id,
            "student_id": p.student_id,
            "window": p.window,
            "risk_probability": p.risk_probability,
            "risk_level": p.risk_level,
            "model_version": p.model_version,
            "features_used": json.loads(p.features_used) if p.features_used else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in preds
    ]


# ─── Explanations ─────────────────────────────────────────────────────────────
@app.post("/api/explain", response_model=ExplanationOut)
def explain(
    req: PredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_student_access(current_user, req.student_id)
    window = req.features.window
    pipe = model_store.get_model(window)

    feature_names = WINDOW_FEATURES[window]
    features_dict = req.features.model_dump(exclude={"window"})
    row_data = {f: features_dict.get(f, 0.0) for f in feature_names}
    student_df = pd.DataFrame([row_data])

    try:
        from src.explainability.shap_explain import (
            generate_explanation_text,
            get_local_shap_values,
        )
        contributions_raw = get_local_shap_values(pipe, student_df, feature_names)
        contributions = [ExplanationItem(**c) for c in contributions_raw]
        top_factors = contributions[:5]
        explanation_text = generate_explanation_text(contributions_raw)
    except Exception as e:
        print(f"  SHAP warning: {e}")
        contributions = []
        top_factors = []
        explanation_text = "Explanation unavailable. Model may not support SHAP yet."

    _log_audit(db, current_user, "EXPLAIN", "explanation", req.student_id, model_store.get_version(window))

    return ExplanationOut(
        student_id=req.student_id,
        contributions=contributions,
        top_factors=top_factors,
        explanation_text=explanation_text,
    )


# ─── Recommendations ──────────────────────────────────────────────────────────
@app.post("/api/recommend", response_model=ActionPlanOut)
def recommend(
    req: PredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_student_access(current_user, req.student_id)
    window = req.features.window
    pipe = model_store.get_model(window)

    feature_names = WINDOW_FEATURES[window]
    features_dict = req.features.model_dump(exclude={"window"})
    row_data = {f: features_dict.get(f, 0.0) for f in feature_names}
    student_df = pd.DataFrame([row_data])

    try:
        from src.config import BINARY_TARGET, PROCESSED_DIR
        train_path = PROCESSED_DIR / f"features_{window}.csv"
        if train_path.exists():
            train_df = pd.read_csv(train_path)
        else:
            train_df = pd.DataFrame([row_data])
            train_df[BINARY_TARGET] = 0

        from src.recourse.action_plan import build_action_plan, format_action_plan_text
        from src.recourse.dice_recourse import generate_counterfactuals

        cf_result = generate_counterfactuals(pipe, student_df, train_df, window)
        steps_raw = build_action_plan(cf_result, row_data)
        steps = [ActionStep(**s) for s in steps_raw]
        plan_text = format_action_plan_text(steps_raw)
    except Exception as e:
        print(f"  Recourse warning: {e}")
        steps = []
        plan_text = "Recommendations unavailable. Please consult your academic advisor."

    return ActionPlanOut(
        student_id=req.student_id,
        steps=steps,
        plan_text=plan_text,
        generated_at=datetime.utcnow(),
    )


# ─── Cohort ───────────────────────────────────────────────────────────────────
@app.get("/api/cohort", response_model=CohortSummary)
def cohort_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("FACULTY", "ADMIN")),
):
    students = db.query(User).filter(User.role == "STUDENT", User.is_active == True).all()
    student_ids = [s.student_id for s in students if s.student_id]

    low = medium = high = 0
    latest_date = None

    for sid in student_ids:
        pred = (
            db.query(Prediction)
            .filter(Prediction.student_id == sid)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        if pred:
            if pred.risk_level == "low":
                low += 1
            elif pred.risk_level == "medium":
                medium += 1
            else:
                high += 1
            if latest_date is None or (pred.created_at and pred.created_at > latest_date):
                latest_date = pred.created_at

    return CohortSummary(
        total_students=len(student_ids),
        low_risk=low,
        medium_risk=medium,
        high_risk=high,
        latest_prediction_date=latest_date.isoformat() if latest_date else None,
    )


@app.get("/api/cohort/students")
def cohort_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("FACULTY", "ADMIN")),
):
    """Return all students with their latest prediction."""
    students = db.query(User).filter(User.role == "STUDENT", User.is_active == True).all()
    result = []
    for student in students:
        pred = None
        if student.student_id:
            pred = (
                db.query(Prediction)
                .filter(Prediction.student_id == student.student_id)
                .order_by(Prediction.created_at.desc())
                .first()
            )
        result.append({
            "id": student.id,
            "username": student.username,
            "student_id": student.student_id,
            "latest_prediction": {
                "risk_probability": pred.risk_probability if pred else None,
                "risk_level": pred.risk_level if pred else "unknown",
                "created_at": pred.created_at.isoformat() if pred and pred.created_at else None,
            } if pred else None,
        })
    return result


# ─── Interventions ─────────────────────────────────────────────────────────────
@app.post("/api/interventions", response_model=InterventionOut)
def record_intervention(
    req: InterventionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("FACULTY", "ADMIN")),
):
    iv = Intervention(
        student_id=req.student_id,
        faculty_id=current_user.id,
        action_taken=req.action_taken,
        notes=req.notes,
        follow_up_date=req.follow_up_date,
    )
    db.add(iv)
    db.commit()
    db.refresh(iv)
    _log_audit(db, current_user, "INTERVENTION", "intervention", str(iv.id))
    return iv


@app.get("/api/interventions/{student_id}", response_model=List[InterventionOut])
def get_interventions(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_student_access(current_user, student_id)
    return (
        db.query(Intervention)
        .filter(Intervention.student_id == student_id)
        .order_by(Intervention.created_at.desc())
        .all()
    )


# ─── Model Registry ───────────────────────────────────────────────────────────
@app.get("/api/models", response_model=List[ModelInfo])
def get_models(current_user: User = Depends(require_role("ADMIN", "FACULTY"))):
    result = []
    for window in ["week4", "week8", "week12"]:
        reg = model_store.registries.get(window, {})
        th_data = model_store.thresholds.get(window, {})
        result.append(ModelInfo(
            model_version=reg.get("model_version", f"model-{window}"),
            window=window,
            training_date=reg.get("training_date"),
            dataset_id=reg.get("dataset_id", "UCI-697"),
            threshold=th_data.get("threshold"),
            available=window in model_store.models,
        ))
    return result


@app.get("/api/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    return db.query(User).all()
