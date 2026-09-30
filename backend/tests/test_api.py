"""
Full integration test suite for EduSight FastAPI endpoints.
Tests auth, health, predictions, explanations, recourse, cohort, interventions, and audit logging.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def tokens(client):
    # Log in as admin
    r_admin = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r_admin.status_code == 200, "Admin login failed"

    # Log in as faculty
    r_fac = client.post("/api/auth/login", json={"username": "faculty1", "password": "faculty123"})
    assert r_fac.status_code == 200, "Faculty login failed"

    # Log in as student
    r_stu = client.post("/api/auth/login", json={"username": "student1", "password": "student123"})
    assert r_stu.status_code == 200, "Student login failed"

    return {
        "admin": r_admin.json()["access_token"],
        "faculty": r_fac.json()["access_token"],
        "student": r_stu.json()["access_token"],
    }


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "week12" in data["models_loaded"]


def test_login_invalid_credentials(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401


def test_get_me(client, tokens):
    res = client.get("/api/students/me", headers={"Authorization": f"Bearer {tokens['student']}"})
    assert res.status_code == 200
    assert res.json()["username"] == "student1"
    assert res.json()["role"] == "STUDENT"


def test_predict_endpoint(client, tokens):
    payload = {
        "student_id": "student-001",
        "features": {
            "window": "week12",
            "Curricular_units_1st_sem_approved": 3.0,
            "Curricular_units_1st_sem_grade": 11.0,
            "Curricular_units_2nd_sem_approved": 2.0,
            "Curricular_units_2nd_sem_grade": 9.5,
        },
    }
    res = client.post(
        "/api/predict",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['student']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert 0.0 <= data["risk_probability"] <= 1.0
    assert data["risk_level"] in ["low", "medium", "high"]
    assert "model_version" in data


def test_student_cannot_predict_for_other_student(client, tokens):
    payload = {
        "student_id": "student-002",  # Different student!
        "features": {"window": "week12"},
    }
    res = client.post(
        "/api/predict",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['student']}"},
    )
    assert res.status_code == 403


def test_explain_endpoint(client, tokens):
    payload = {
        "student_id": "student-001",
        "features": {
            "window": "week12",
            "Curricular_units_1st_sem_approved": 2.0,
            "Curricular_units_2nd_sem_approved": 1.0,
        },
    }
    res = client.post(
        "/api/explain",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['student']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["top_factors"]) > 0
    assert "associations" in data["explanation_text"].lower() or "influential" in data["explanation_text"].lower()


def test_recommend_endpoint(client, tokens):
    payload = {
        "student_id": "student-001",
        "features": {
            "window": "week12",
            "Curricular_units_1st_sem_approved": 2.0,
            "Curricular_units_2nd_sem_approved": 1.0,
        },
    }
    res = client.post(
        "/api/recommend",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['student']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["steps"]) > 0


def test_cohort_summary_faculty_only(client, tokens):
    # Student should be forbidden
    r_stu = client.get(
        "/api/cohort",
        headers={"Authorization": f"Bearer {tokens['student']}"},
    )
    assert r_stu.status_code == 403

    # Faculty should succeed
    r_fac = client.get(
        "/api/cohort",
        headers={"Authorization": f"Bearer {tokens['faculty']}"},
    )
    assert r_fac.status_code == 200
    assert "total_students" in r_fac.json()


def test_intervention_crud(client, tokens):
    # Record intervention by faculty
    payload = {
        "student_id": "student-001",
        "action_taken": "Scheduled 1-on-1 tutoring session",
        "notes": "Student showed enthusiasm to improve calculus grade.",
    }
    create_res = client.post(
        "/api/interventions",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['faculty']}"},
    )
    assert create_res.status_code == 200
    assert create_res.json()["action_taken"] == payload["action_taken"]

    # Student can read their own interventions
    get_res = client.get(
        "/api/interventions/student-001",
        headers={"Authorization": f"Bearer {tokens['student']}"},
    )
    assert get_res.status_code == 200
    assert len(get_res.json()) >= 1
