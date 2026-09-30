"""
Model registry for EduSight.
Tracks model versions, dataset versions, thresholds, and metadata.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import MODELS_DIR, RANDOM_SEED


def get_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=MODELS_DIR.parent.parent
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def get_python_packages() -> dict:
    import importlib
    packages = {}
    for pkg in ["pandas", "numpy", "sklearn", "xgboost", "shap", "dice_ml", "imblearn", "fastapi"]:
        try:
            m = importlib.import_module(pkg if pkg != "sklearn" else "sklearn")
            packages[pkg] = getattr(m, "__version__", "unknown")
        except ImportError:
            packages[pkg] = "not installed"
    return packages


def register_model(
    model_name: str,
    window: str,
    dataset_id: str = "UCI-697",
    feature_version: str = "v1",
    threshold: float = None,
    calibration_method: str = "isotonic",
    metrics: dict = None,
) -> dict:
    """Create and save model registry entry."""
    entry = {
        "model_version": f"{model_name}-{window}-001",
        "model_name": model_name,
        "window": window,
        "dataset_id": dataset_id,
        "feature_version": feature_version,
        "threshold": threshold,
        "threshold_version": f"threshold-{window}-001",
        "calibration_method": calibration_method,
        "training_date": datetime.now().isoformat(),
        "training_commit": get_git_commit(),
        "random_seed": RANDOM_SEED,
        "python_packages": get_python_packages(),
        "metrics": metrics or {},
        "note": "Model trained on UCI-697 with documented experimental binary target mapping.",
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / f"registry_{model_name}_{window}.json"
    with open(path, "w") as f:
        json.dump(entry, f, indent=2)
    print(f"Registry entry → {path}")
    return entry


def load_registry(window: str, model_name: str = "xgboost") -> dict:
    path = MODELS_DIR / f"registry_{model_name}_{window}.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)
