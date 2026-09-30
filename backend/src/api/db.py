"""
Database setup for EduSight API.
SQLite + SQLAlchemy ORM. No PostgreSQL required.
"""
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Database URL — SQLite file in data/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "edusight.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite only
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="STUDENT")  # STUDENT, FACULTY, ADMIN
    student_id = Column(String(64), nullable=True, index=True)     # anonymous ML identifier
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(64), nullable=False, index=True)
    window = Column(String(20), nullable=False, default="week12")
    risk_probability = Column(Float, nullable=False)
    risk_level = Column(String(10), nullable=False)       # low, medium, high
    model_version = Column(String(60), nullable=True)
    threshold_version = Column(String(60), nullable=True)
    features_used = Column(Text, nullable=True)           # JSON string of feature values
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(64), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_taken = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    follow_up_date = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(80), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    model_version = Column(String(60), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)


def get_db():
    """FastAPI dependency: yields DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"✓ Database tables created at {DB_PATH}")
