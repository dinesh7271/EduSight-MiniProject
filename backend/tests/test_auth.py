"""
Authentication and Authorization unit tests for EduSight.
Verifies password hashing, JWT creation/verification, role enforcement, and data isolation.
"""
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
    verify_student_access,
)
from src.api.db import User


def test_password_hash_and_verify():
    pwd = "SecretAcademicPassword#2026"
    h = hash_password(pwd)
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password(pwd, h)
    assert not verify_password("WrongPassword", h)


def test_jwt_token_roundtrip():
    payload = {"sub": "student1", "role": "STUDENT"}
    token = create_access_token(payload)
    decoded = decode_token(token)

    assert decoded["sub"] == "student1"
    assert decoded["role"] == "STUDENT"
    assert "exp" in decoded


def test_invalid_jwt_token_rejected():
    with pytest.raises(HTTPException) as exc:
        decode_token("invalid.token.structure")
    assert exc.value.status_code == 401


def test_student_data_isolation():
    student_user = User(
        id=3,
        username="student1",
        role="STUDENT",
        student_id="student-001",
    )
    # Student accessing their own data: should NOT raise
    verify_student_access(student_user, "student-001")

    # Student trying to access another student's data: MUST raise 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        verify_student_access(student_user, "student-002")
    assert exc.value.status_code == 403


def test_faculty_and_admin_bypass_student_isolation():
    faculty_user = User(id=2, username="faculty1", role="FACULTY", student_id=None)
    admin_user = User(id=1, username="admin", role="ADMIN", student_id=None)

    # Faculty can view any student
    verify_student_access(faculty_user, "student-001")
    verify_student_access(faculty_user, "student-002")

    # Admin can view any student
    verify_student_access(admin_user, "student-001")
