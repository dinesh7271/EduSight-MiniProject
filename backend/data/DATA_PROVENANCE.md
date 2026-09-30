# EduSight — Data Provenance

## Dataset 1: Predict Students' Dropout and Academic Success

| Field | Value |
|---|---|
| **Dataset Name** | Predict Students' Dropout and Academic Success |
| **Dataset ID** | UCI-697 |
| **Official Source** | UCI Machine Learning Repository |
| **Official URL** | https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success |
| **License** | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **DOI** | 10.24432/C5GP7S |
| **Download Date** | 2026-09-30 |
| **Dataset Version** | 1 |
| **Original Row Count** | 4,424 |
| **Original Column Count** | 37 (36 features + 1 target) |

### Target Definition (Native)

```
Target: Dropout / Enrolled / Graduate
```

### Experimental Binary Mapping (EduSight)

```
Dropout  → at_risk = 1
Enrolled → at_risk = 0  (experimental; not all enrolled students are risk-free)
Graduate → at_risk = 0
```

> **IMPORTANT**: This binary mapping is an **experimental target definition**
> created for the EduSight early-warning experiment. It does NOT rename the
> original dataset's target. Any performance metrics reported by EduSight
> correspond to this experimental definition, not the original 3-class task.

### Features Used

See `src/config.py` for the exact feature lists per prediction window (week4/week8/week12).

### Features Excluded from Model

| Feature | Reason |
|---|---|
| `Target` | **Is the label** — absolute exclusion |
| `at_risk` | Derived from Target — absolute exclusion |
| `Curricular_units_1st_sem_grade` | Excluded from Week 4 window (temporal leakage) |
| `Curricular_units_2nd_sem_*` | Excluded from Week 4 and Week 8 windows (temporal leakage) |

### Transformations Applied

1. Column name normalization (strip spaces, parentheses → underscores)
2. Exact duplicate row removal (if any found)
3. Binary target creation from native `Target` column

### Missing Value Handling

No missing values found in this dataset. If discovered: document count, report, do NOT impute without explicit justification.

### Train/Test Split

| Split | Fraction | Method |
|---|---|---|
| Train | 80% | `train_test_split(stratify=y, random_state=42)` |
| Test | 20% | Held out, used only for final evaluation |

Cross-validation (5-fold StratifiedKFold) used on training set for threshold selection.
Test set was **never used** for threshold selection or hyperparameter tuning.

### SHA256

Recorded in `data/raw/uci697/provenance.json` after download.

---

## Dataset 2: OULAD (Planned — not yet downloaded)

| Field | Value |
|---|---|
| **Dataset Name** | Open University Learning Analytics Dataset |
| **Dataset ID** | OULAD |
| **Official URL** | https://analyse.kmi.open.ac.uk/open_dataset |
| **Status** | **PENDING** — Not yet downloaded |

> OULAD temporal experiments are planned as Phase 2. Results will be added here
> after download and processing.

---

## Institutional Data

| Field | Value |
|---|---|
| **Status** | **BLOCKED** — No authorization obtained |

Institutional data requires explicit authorization with privacy controls.
Until authorization is obtained, all model training uses public datasets only.
