# EduSight — Information Security & Access Control Policy

## 1. Authentication Standards
- **Token Format**: JSON Web Tokens (JWT) signed via HMAC-SHA256 (`HS256`).
- **Token Lifetime**: 24-hour expiration window.
- **Password Storage**: Passwords are saved as cryptographically salted hashes using standard PBKDF2-HMAC-SHA256 with 100,000 iterative rounds and unique 128-bit random salts per account. Plaintext passwords are never logged, cached, or persisted.

---

## 2. Role-Based Access Control (RBAC)

| Role | Accessible Endpoints | Permissions |
|---|---|---|
| **STUDENT** | `/api/students/me`, `/api/predict`, `/api/explain`, `/api/recommend`, `/api/interventions/{id}` | Read-only access to own assessment, SHAP factors, and recommendations. Cannot access other students' records or cohort aggregates. |
| **FACULTY** | All above + `/api/cohort`, `/api/cohort/students`, `/api/interventions` (POST), `/api/models` | View course-level cohort statistics, inspect individual student profiles, submit advisor intervention notes. |
| **ADMIN** | All above + `/api/users`, `/api/auth/register` | Manage system accounts, register new personnel, monitor system health and model registry. |

---

## 3. Student Data Isolation Rule
In any endpoint receiving a `student_id` parameter, the authorization layer verifies that if the authenticated caller has the `STUDENT` role, the requested `student_id` matches the caller's JWT `student_id` claim exactly. Any mismatch triggers an immediate `403 Forbidden` response.

---

## 4. API Security & CORS
- Cross-Origin Resource Sharing (CORS) is explicitly constrained to authorized frontend origins (e.g. `http://localhost:5173`).
- All requests entering mutating or privileged routes undergo strict Pydantic v2 schema validation.
- SQL injection risks are eliminated by using SQLAlchemy parameterized queries across all database operations.
