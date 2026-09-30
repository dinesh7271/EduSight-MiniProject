# EduSight — Project Specification & Architectural Blueprint

## 1. System Vision & Objective
EduSight is an **AI-powered academic early-warning and decision-support system** engineered for higher education institutions. Its purpose is to identify students who are at risk of academic failure or dropout early enough in a term (Weeks 4, 8, and 12) for academic advisors and faculty to intervene with meaningful support.

EduSight is designed around three strict foundational principles:
1. **Decision Support, Not Automated Decisions**: All predictions are probabilistic indicators for human advisors. EduSight never automates punitive actions, grade adjustments, or status changes.
2. **Actionability and Counterfactual Recourse**: Predicting risk without actionable guidance is unhelpful. EduSight pairs every risk estimate with actionable recourse—explaining what specific, feasible changes can reduce predicted risk without altering immutable demographic traits.
3. **Empirical Authenticity**: Zero data fabrication, no synthetic metrics, strict temporal leakage prevention, and full data provenance.

---

## 2. Dataset Strategy & Temporal Windows

### 2.1 Primary Dataset: UCI 697
- **Name**: Predict Students' Dropout and Academic Success
- **Rows**: 4,424 students
- **Raw Features**: 36 features across demographic, socioeconomic, macro-economic, and semester-level academic performance.
- **Native Target**: `Dropout`, `Enrolled`, `Graduate` (3-class).
- **Experimental Binary Target**:
  - `Dropout` $\rightarrow 1$ (`at_risk`)
  - `Enrolled` / `Graduate` $\rightarrow 0$ (`not_at_risk`)
  - *Documented as an experimental research definition, not altering the underlying dataset.*

### 2.2 Temporal Prediction Windows
To simulate true operational conditions throughout an academic term, three temporal feature sets are enforced:
- **Week 4 (Enrollment & Demographic Baseline)**: 29 features. Includes admission grades, demographic indicators, socioeconomics, and 1st semester enrollment course loads. Zero internal grades.
- **Week 8 (Mid-Semester Internal Checkpoint)**: 30 features. Adds 1st semester grade (`Curricular_units_1st_sem_grade`).
- **Week 12 (Comprehensive Term Status)**: 36 features. Adds all 2nd semester curricular units enrolled, evaluated, approved, and grades.

---

## 3. Machine Learning Architecture

### 3.1 Model Portfolio & Benchmark Matrix
EduSight evaluates four distinct model archetypes across all three prediction windows:
1. **Dummy Baseline**: Stratified prior frequency.
2. **Logistic Regression (L2)**: Scaled linear baseline.
3. **Random Forest (400 Trees)**: Non-linear ensemble with balanced class weights.
4. **XGBoost Classifier**: Gradient boosted decision trees with depth=5, subsample=0.8, colsample=0.8.

### 3.2 Imbalance & Leakage Prevention Policy
- **SMOTE Isolation**: Class balancing (SMOTE) is strictly encapsulated inside `imblearn.pipeline.Pipeline`. SMOTE runs *only* on the training folds of cross-validation. It is **never** applied to the whole dataset or to test sets.
- **Cost-Weighted Thresholding**: Decision thresholds are optimized using cross-validation validation probabilities by weighting False Negatives (missing a struggling student) **5× more costly** than False Positives (false alarm).
- **Probability Calibration**: All final models undergo isotonic probability calibration to ensure that a predicted probability of 0.80 aligns with ~80% empirical risk.

---

## 4. Explainability & Counterfactual Recourse

### 4.1 Local & Global SHAP Explainability
- Evaluated via `shap.TreeExplainer` on the fitted tree ensembles.
- Produces local feature contribution vectors for each student.
- **Strict Language Rules**:
  - Valid: *"Feature X contributed to the predicted risk score."*
  - Valid: *"Attendance was an important factor in this prediction."*
  - Prohibited: *"Low attendance caused the student to fail."*
  - Prohibited: *"The student will definitely drop out."*

### 4.2 Constrained Counterfactual Recourse (DiCE)
- Solves for the minimal perturbation required to move a student from `at_risk = 1` to `not_at_risk = 0`.
- **Immutability Constraints**: Demographic features (`Gender`, `Age_at_enrollment`, `Nationality`, parents' qualifications/occupations) are strictly locked and cannot be changed.
- **Actionability Windows**: Only controllable academic behaviors (approved units, grades, attendance, fee payment) are permitted to vary.
- **Feasibility Bounds**: Grades are mathematically bounded by remaining credit units (maximum 20.0).

---

## 5. Technology Stack & Deployment

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | React 18 + Vite | Fast, responsive Single Page Application |
| **Charts** | Recharts | SVG-based responsive data visualizations |
| **Backend API** | FastAPI (Python 3.14) | High-performance asynchronous REST API with OpenAPI |
| **Database** | SQLite + SQLAlchemy ORM | Zero-setup relational storage with full ACID compliance |
| **Authentication** | JWT (HS256) + PBKDF2-HMAC-SHA256 | Cryptographically secure, stateless token authentication |
| **ML Engine** | scikit-learn, XGBoost, imbalanced-learn, SHAP, DiCE | Industry-standard scientific machine learning stack |
