"""
OULAD Dataset Ingestion Module for EduSight.
Downloads and extracts the Open University Learning Analytics Dataset.
"""
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import OULAD_RAW, RAW_DIR

OULAD_URL = "https://analyse.kmi.open.ac.uk/open_dataset/download"
EXPECTED_TABLES = [
    "courses.csv",
    "assessments.csv",
    "vle.csv",
    "studentInfo.csv",
    "studentRegistration.csv",
    "studentAssessment.csv",
    "studentVle.csv",
]


def download_oulad(dest_dir: Path = OULAD_RAW) -> Path:
    """Download and extract OULAD zip archive."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "oulad_raw.zip"

    # Check if already extracted
    existing = [t for t in EXPECTED_TABLES if (dest_dir / t).exists()]
    if len(existing) == len(EXPECTED_TABLES):
        print(f"✓ OULAD all {len(EXPECTED_TABLES)} tables already present in {dest_dir}")
        return dest_dir

    print(f"Downloading OULAD dataset from:\n  {OULAD_URL}")
    print("  Note: OULAD is ~140MB compressed, this may take a few minutes...")

    try:
        headers = {"User-Agent": "EduSight-Academic-Research/1.0"}
        with requests.get(OULAD_URL, stream=True, timeout=300, headers=headers) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        print(f"  Downloaded archive → {zip_path}")
    except Exception as e:
        print(f"  ⚠ Automatic download failed: {e}")
        print("  Manual download instruction:")
        print(f"    Download zip from {OULAD_URL}")
        print(f"    Extract CSVs to {dest_dir}/")
        return dest_dir

    # Extract
    print("  Extracting archive...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    print("  ✓ Extracted.")

    # Flatten if nested directory
    for item in dest_dir.rglob("*.csv"):
        target = dest_dir / item.name
        if item != target and not target.exists():
            shutil.move(str(item), str(target))

    # Compute provenance
    record_oulad_provenance(dest_dir)
    return dest_dir


def record_oulad_provenance(dest_dir: Path):
    table_stats = {}
    for table_name in EXPECTED_TABLES:
        t_path = dest_dir / table_name
        if t_path.exists():
            with open(t_path, "rb") as f:
                sha = hashlib.sha256(f.read(1024 * 1024)).hexdigest()
            table_stats[table_name] = {
                "file_size_bytes": t_path.stat().st_size,
                "partial_sha256": sha,
            }

    provenance = {
        "dataset_name": "Open University Learning Analytics Dataset (OULAD)",
        "source_url": OULAD_URL,
        "download_date": datetime.now().isoformat(),
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "tables": table_stats,
    }

    prov_path = dest_dir / "provenance.json"
    with open(prov_path, "w") as f:
        json.dump(provenance, f, indent=2)
    print(f"  OULAD provenance → {prov_path}")


if __name__ == "__main__":
    download_oulad()
