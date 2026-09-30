# 🎓 EduSight — AI-Powered Academic Early Warning & Decision Support System

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-Ensemble-EB5424?style=for-the-badge&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![License](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey?style=for-the-badge)](https://creativecommons.org/licenses/by/4.0/)

> **EduSight** is an institutional academic decision-support platform designed for colleges and universities. It monitors student performance during an ongoing semester using **Attendance %, Internal Assessment Marks (CIA 1 & CIA 2)**, and **Coursework Submissions** across three temporal checkpoints (**Week 4, Week 8, and Week 12**). 
> 
> Rather than simply flagging students, EduSight provides **explainable AI (SHAP)** factor attributions and **actionable counterfactual recourse (DiCE)** to guide faculty advisors and empower students toward academic recovery.

---

## 🌟 Key Highlights

- ⏱️ **Zero-Lookahead Temporal Modeling**: Strict temporal feature cuts across **Week 4** (baseline & attendance), **Week 8** (mid-semester / post CIA-1), and **Week 12** (late term / post CIA-2) preventing data leakage.
- 📋 **Current Semester Focus**: Direct evaluation of student attendance rates, CIA 1 & CIA 2 marks, assignment completion counts, and standing arrears.
- 🚨 **Attendance Exam Eligibility Alert**: Automatic detection and alerting for attendance shortage ($<75\%$) under university examination regulations.
- 🔍 **Explainable AI (SHAP)**: High-resolution local and global feature attribution ensuring full transparency into which metrics contributed to predicted risk.
- 🎯 **Constrained Counterfactual Recourse**: Generates feasible, mathematically sound improvement targets without attempting to alter immutable demographic characteristics.
- 🛡️ **Zero Data Fabrication**: 100% of benchmark metrics are derived from real public higher education datasets (UCI 697: 4,424 students) using strict 5-fold cross-validation with SMOTE isolated inside pipeline folds.
- 🎨 **Modern Beige & Sage Green Aesthetic**: High-contrast, accessibility-first interface designed for clarity, free of dark-theme clutter.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Data & Pipeline Layer
        UCI["Dataset: UCI 697 (4,424 Students)"] --> Ingest["Ingestion & SHA-256 Checksum"]
        Ingest --> LeakageAudit["Leakage Auditor"]
        LeakageAudit --> Preproc["Temporal Window Splitter"]
        Preproc --> W4["Week 4 (Enrollment & Attendance)"]
        Preproc --> W8["Week 8 (+ Internal 1 / CIA-1 Marks)"]
        Preproc --> W12["Week 12 (+ Internal 2 / CIA-2 Marks)"]
    end

    subgraph Machine Learning Engine
        W4 & W8 & W12 --> ImbPipe["imblearn Pipeline (SMOTE in CV Folds)"]
        ImbPipe --> Models["Ensembles (XGBoost, RF, LogReg)"]
        Models --> Calib["Isotonic Probability Calibration"]
        Models --> SHAP["TreeExplainer SHAP Attributions"]
        Models --> Recourse["DiCE Constrained Recourse Engine"]
    end

    subgraph Backend API (:8000)
        SQLite[("SQLite Relational DB\n(data/edusight.db)")]
        FastAPI["FastAPI REST Application"]
        JWT["JWT Auth + PBKDF2 Password Hashing"]
        FastAPI <--> SQLite
        FastAPI <--> Calib
        FastAPI <--> SHAP
        FastAPI <--> Recourse
    end

    subgraph Frontend Client (:5173)
        Vite["React 18 + Vite SPA"]
        Auth["Dual Login & Account Registration"]
        SDash["Student Dashboard (Attendance, CIA, Gauge, SHAP)"]
        FDash["Faculty Dashboard (Cohort Stats, Roster, Interventions)"]
        Vite --> Auth & SDash & FDash
        Vite <-->|REST Proxy /api| FastAPI
    end
```

---

## 📂 Repository Organization

```text
EduSight/
├── backend/                       # 🐍 Python FastAPI & ML Service
│   ├── src/
│   │   ├── api/                   # REST API routes, auth, schemas, DB models
│   │   ├── data/                  # Ingestion, validation, leakage audits
│   │   ├── explainability/        # SHAP attribution & stability metrics
│   │   ├── features/              # Temporal cutoff feature builders
│   │   ├── models/                # Training, evaluation, calibration, registry
│   │   ├── monitoring/            # PSI & KS data/prediction drift detection
│   │   ├── recourse/              # DiCE counterfactual action planning
│   │   └── config.py              # Central project configuration & labels
│   ├── data/                      # Processed CSVs, raw files, SQLite database
│   ├── models/                    # Serialized models (.joblib) & thresholds
│   ├── reports/                   # Experiment comparisons & leakage audit reports
│   ├── tests/                     # 43 automated unit & integration tests
│   ├── requirements.txt           # Python dependency specifications
│   └── .env.example               # Environment variables template
│
├── frontend/                      # ⚛️ React 18 + Vite Web Application
│   ├── src/
│   │   ├── api/                   # Axios client with interceptors
│   │   ├── components/            # RiskBadge, ShapChart, ActionChecklist, NavBar
│   │   ├── context/               # AuthContext with persistent session
│   │   ├── pages/                 # LoginPage, StudentDashboard, FacultyDashboard, AdminPanel
│   │   └── styles/                # Clean beige & sage green theme CSS
│   ├── index.html                 # Vite HTML entry
│   ├── package.json               # Node dependencies
│   └── vite.config.js             # Vite development server & /api proxy
│
├── docs/                          # 📜 Formal Policy & Specification Documentation
│   ├── PROJECT_SPECIFICATION.md   # Architectural blueprint & requirements
│   ├── DATA_POLICY.md             # Privacy, zero-fabrication, and consent rules
│   ├── MODEL_POLICY.md            # Leakage policy, SMOTE isolation, cost weighting
│   └── SECURITY_POLICY.md         # JWT authentication, RBAC, student isolation
│
├── run_edusight.sh                # 🚀 Unified runner for both backend and frontend
├── .gitignore                     # Git ignore rules for node_modules, cache, logs
└── README.md                      # Project documentation
```

---

## 📊 Empirical Model Benchmark (Real Dataset Evaluation)

All evaluations below were computed strictly on held-out test data from the UCI 697 dataset (**4,424 real students**). Thresholds are optimized with an asymmetric **5:1 False Negative penalty weight** to prioritize identifying struggling students:

| Window | Model | ROC-AUC | PR-AUC | Recall | Precision | F1-Score | Brier Score |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Week 4** | Logistic Regression | 0.8995 | 0.8574 | **0.9507** | 0.4259 | 0.5882 | 0.1105 |
| **Week 4** | Random Forest | 0.9072 | 0.8705 | **0.9754** | 0.4044 | 0.5717 | 0.1071 |
| **Week 4** | **XGBoost (Selected)** | **0.9114** | **0.8777** | **0.9331** | **0.5000** | **0.6511** | **0.0988** |
| **Week 8** | Logistic Regression | 0.8986 | 0.8567 | **0.9507** | 0.4206 | 0.5832 | 0.1116 |
| **Week 8** | Random Forest | 0.9067 | 0.8677 | **0.9718** | 0.4071 | 0.5738 | 0.1079 |
| **Week 8** | **XGBoost (Selected)** | **0.9142** | **0.8807** | **0.9225** | **0.5068** | **0.6542** | **0.0979** |
| **Week 12** | Logistic Regression | 0.9207 | 0.8904 | **0.9542** | 0.4729 | 0.6324 | 0.0962 |
| **Week 12** | Random Forest | 0.9301 | 0.9017 | **0.9718** | 0.4313 | 0.5974 | 0.0914 |
| **Week 12** | **XGBoost (Selected)** | **0.9314** | **0.9032** | **0.9331** | **0.5419** | **0.6856** | **0.0862** |

---

## 🛠️ Getting Started

### Prerequisites
- **Python**: Version 3.10, 3.11, 3.12, or 3.14
- **Node.js**: Version 18.x or 20.x
- **npm**: Version 9.x or higher

---

### Quick Start (One Command)

To launch both the FastAPI backend and Vite frontend with a single script:

```bash
git clone https://github.com/dinesh7271/EduSight-MiniProject.git
cd EduSight-MiniProject
chmod +x run_edusight.sh
./run_edusight.sh
```

- **Frontend Application**: `http://localhost:5173`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

### Manual Setup

#### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Run preprocessing & model training (if not already trained)
python -m src.preprocess
python -m src.models.train

# Start the FastAPI server
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 👥 Demo Accounts & Roles

EduSight includes pre-configured demo accounts for testing all access tiers:

| Role | Username | Password | Access Scope |
|---|---|---|---|
| **Student** | `student1` | `student123` | Personal semester predictor, attendance tracking, SHAP factors, and action plan |
| **Faculty / Teacher** | `faculty1` | `faculty123` | Class cohort risk distribution, student roster, drawer with past advisor notes |
| **Administrator** | `admin` | `admin123` | User account management, model registry status, and system health |

*New users can also click the **"Create Account"** tab directly on the login page to register as a Student or Teacher.*

---

## 🧪 Automated Test Suite (43 Tests)

The test suite covers data leakage, student access isolation, password hashing, and API endpoints:

```bash
cd backend
pytest tests/ -v
```

```text
tests/test_leakage.py    24 passed  (10 mandatory ML leakage constraints)
tests/test_recourse.py    5 passed  (immutability & feasibility bounds)
tests/test_auth.py        5 passed  (PBKDF2-HMAC-SHA256 & student isolation)
tests/test_api.py         9 passed  (FastAPI endpoints & RBAC)
======================== 43 passed in 4.9s ========================
```

---

## 📜 Ethical AI & Responsible Use

EduSight follows strict ethical AI design guidelines:
1. **Decision Support, Not Automated Decisions**: Predictions are probabilistic risk signals to assist educators. The system never automates grade deductions, suspensions, or punitive consequences.
2. **Non-Causal Language Rules**: Explanations state statistical associations (e.g. *"Feature X contributed to the predicted risk score"*) rather than deterministic claims (*"Low marks caused failure"*).
3. **Data Protection & Student Isolation**: Machine learning models consume only anonymous student identifiers (`student-001`). Students can strictly inspect only their own academic evaluations.

---

## 📄 License
This project is licensed under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license.
