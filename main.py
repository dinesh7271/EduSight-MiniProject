"""
EduSight — Root Entry Point.

Allows running the FastAPI application directly from the root workspace directory:
    uvicorn main:app --port 8000 --reload
or:
    python3 -m uvicorn main:app --port 8000 --reload
"""
import sys
from pathlib import Path

# Add backend directory to sys.path so 'src' and backend modules resolve seamlessly
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import the FastAPI app instance from backend/src/api/main.py
from src.api.main import app

__all__ = ["app"]
