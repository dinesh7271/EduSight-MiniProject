"""
Data ingestion for EduSight — UCI 697 dataset.
Downloads from official UCI ML repository and records provenance.

RULE: Never modify raw files. Never invent columns or data.
"""
import hashlib
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import RAW_DIR, REPORTS_DIR, UCI697_RAW

UCI697_URL = "https://archive.ics.uci.edu/static/public/697/predict+students+dropout+and+academic+success.zip"
UCI697_ZIP = RAW_DIR / "uci697" / "uci697_raw.zip"
UCI697_DIR = RAW_DIR / "uci697"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download_uci697() -> dict:
    """Download UCI 697 dataset from official source. Returns provenance dict."""
    UCI697_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading UCI 697 from:\n  {UCI697_URL}")
    resp = requests.get(UCI697_URL, stream=True, timeout=120)
    resp.raise_for_status()

    with open(UCI697_ZIP, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
    print(f"Saved zip → {UCI697_ZIP}")

    # Extract
    import zipfile
    with zipfile.ZipFile(UCI697_ZIP, "r") as z:
        z.extractall(UCI697_DIR)
    print("Extracted archive.")

    # Find the CSV
    candidates = list(UCI697_DIR.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(
            "No CSV found after extraction. Check archive contents."
        )
    csv_path = candidates[0]

    # Rename to canonical name if needed
    target = UCI697_DIR / "data.csv"
    if csv_path != target:
        shutil.copy2(csv_path, target)
    print(f"Dataset CSV → {target}")

    sha = sha256_file(target)
    print(f"SHA256: {sha}")

    # Count rows/cols
    with open(target, encoding="utf-8") as f:
        lines = f.readlines()
    n_rows = len(lines) - 1  # header
    n_cols = len(lines[0].split(";")) if ";" in lines[0] else len(lines[0].split(","))

    provenance = {
        "dataset_name": "Predict Students' Dropout and Academic Success",
        "dataset_id": "UCI-697",
        "official_source": "UCI Machine Learning Repository",
        "official_url": "https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success",
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "doi": "10.24432/C5GP7S",
        "download_date": str(date.today()),
        "dataset_version": "1",
        "original_file": str(target.relative_to(UCI697_DIR.parent.parent.parent)),
        "original_row_count": n_rows,
        "original_column_count": n_cols,
        "sha256": sha,
        "native_target": "Target (Dropout / Enrolled / Graduate)",
        "experimental_binary_target": "at_risk (Dropout=1, Enrolled/Graduate=0)",
        "target_mapping_documented": True,
    }
    return provenance


def save_provenance(provenance: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(provenance, f, indent=2)
    print(f"Provenance saved → {path}")


def generate_data_inventory(provenance: dict):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    inv_path = REPORTS_DIR / "data_inventory.json"
    inventory = {
        "datasets": [provenance],
        "generated_at": str(date.today()),
        "note": "All datasets from official public sources. No synthetic data used for model training.",
    }
    with open(inv_path, "w") as f:
        json.dump(inventory, f, indent=2)
    print(f"Data inventory → {inv_path}")


if __name__ == "__main__":
    prov = download_uci697()
    save_provenance(prov, RAW_DIR / "uci697" / "provenance.json")
    generate_data_inventory(prov)
    print("\n✓ UCI 697 ingestion complete.")
