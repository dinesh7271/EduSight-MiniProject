# EduSight — Institutional Data Governance & Privacy Policy

## 1. Principles of Data Stewardship
Academic data involves sensitive personal, socioeconomic, and educational records. EduSight adheres strictly to the highest standards of data minimization, purpose limitation, transparency, and integrity.

---

## 2. Zero-Fabrication Policy
- Under no circumstances shall synthetic data, simulated mock metrics, or fabricated outcomes be presented as authentic empirical findings.
- All evaluation figures (Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, Brier score) must derive strictly from executed code on verifiable data sources.
- Any exploratory or synthetic test data used during testing must be explicitly demarcated in code and excluded from institutional reporting.

---

## 3. Strict Student Privacy & PII Isolation
1. **De-identification**: Machine learning pipelines consume only anonymous student identifiers (e.g., `student-001`). Personally Identifiable Information (names, physical addresses, student IDs, personal email addresses) are isolated at the database user layer and never fed into feature matrices.
2. **Access Isolation**:
   - Students can **only** inspect their own risk assessments and recommendations.
   - Faculty members can view cohort-level summaries and individual profiles of students in their assigned courses.
   - Administrators possess user management capabilities but cannot alter model outputs or audit logs.

---

## 4. Consent and Institutional Authorization
- Public datasets (UCI 697, OULAD) are used strictly within their CC BY 4.0 licensing terms.
- **Institutional Deployment Rule**: Real institutional records require explicit institutional authorization, student consent disclosures, and compliance with applicable data privacy frameworks (such as FERPA or GDPR) before any live ingestion occurs.
- Until authorization is obtained, live deployments are blocked from reading unapproved student databases.

---

## 5. Audit Logging and Provenance
- Every raw dataset is verified using SHA-256 cryptographic checksums stored in `provenance.json`.
- All prediction requests, explanation generations, and recorded advisor interventions are permanently recorded in the `audit_log` table with timestamps, user IDs, and model version identifiers.
