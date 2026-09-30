# EduSight — Build Guide

A practical, start-to-finish plan for building the project. Follow the phases in order.
Nothing here needs a GPU, paid API, or anything beyond a normal laptop.

---

## 0. Repository layout

Create this first. Everything else drops into it.

```
edusight/
├── data/
│   ├── raw/                 # downloaded datasets, never edited
│   ├── processed/           # output of the preprocessing step
│   └── README.md            # where each file came from
├── notebooks/
│   ├── 01_explore.ipynb
│   ├── 02_baseline_models.ipynb
│   ├── 03_shap.ipynb
│   ├── 04_counterfactuals.ipynb
│   └── 05_earliness.ipynb
├── src/
│   ├── config.py            # feature lists, paths, constants — ONE source of truth
│   ├── preprocess.py        # M1
│   ├── train.py             # M2
│   ├── evaluate.py          # M2
│   ├── explain.py           # M3
│   ├── recourse.py          # M4
│   └── api/
│       ├── main.py          # FastAPI app
│       ├── schemas.py       # Pydantic request/response models
│       ├── auth.py          # M6
│       └── db.py
├── models/                  # model.joblib, explainer.joblib, threshold.json
├── frontend/                # React app (Vite)
├── requirements.txt
└── README.md
```

`requirements.txt`:

```
pandas==2.2.*
numpy==1.26.*
scikit-learn==1.5.*
xgboost==2.1.*
imbalanced-learn==0.12.*
shap==0.46.*
dice-ml==0.11
joblib
matplotlib
fastapi
uvicorn[standard]
pydantic
sqlalchemy
python-jose[cryptography]
passlib[bcrypt]
python-multipart
jupyter
```

---

## Phase 1 — Data (weeks 1–2)

### 1.1 Download the public dataset

UCI Student Performance: <https://archive.ics.uci.edu/dataset/320/student>
Gives you `student-mat.csv` (395 rows) and `student-por.csv` (649 rows), 33 columns each, semicolon-separated. Use `student-por.csv` — more rows.

```python
df = pd.read_csv("data/raw/student-por.csv", sep=";")
```

Useful columns: `failures` (past failures), `studytime`, `absences`, `higher`, `schoolsup`,
`famsup`, `goout`, `health`, `Medu`/`Fedu`, `G1`, `G2`, `G3` (period grades, 0–20).

### 1.2 Define the target — do this before touching a model

```python
# G3 is the final grade (0-20). Pass mark is 10.
df["at_risk"] = (df["G3"] < 10).astype(int)
```

### 1.3 The leakage rule (most important rule in the project)

`G3` becomes the label, so it can never be a feature. `G1` and `G2` are the tricky ones:
they are *mid-term grades*, which is exactly what your week-4/week-8 snapshots represent.

Run and report **two settings**:

| Setting | Features | Meaning |
|---|---|---|
| Week 4 | no G1, no G2 | predict from behaviour + background only |
| Week 8 | G1 only | after first internal |
| Week 12 | G1 + G2 | after second internal |

Never include G3. If anyone asks "why is your accuracy 92%?", the answer must not be
"because G2 was in the features."

### 1.4 Institutional data (run this in parallel — it takes weeks)

Write a one-page request to your HOD/guide asking for anonymised records:
attendance %, internal 1, internal 2, assignment submission count, arrears, previous GPA.
No names, no register numbers — ask for a row ID only. If it doesn't come through,
the public dataset alone is enough for a mini project. Don't let this block you.

### 1.5 Deliverable

`src/preprocess.py` that reads raw CSV → writes `data/processed/features_week{4,8,12}.csv`
plus a `feature_manifest.json` listing which columns are in each.

---

## Phase 2 — Models (weeks 3–4)

### 2.1 Split first, resample second

```python
from sklearn.model_selection import StratifiedKFold
from imblearn.pipeline import Pipeline          # imblearn's Pipeline, NOT sklearn's
from imblearn.over_sampling import SMOTE

pipe = Pipeline([
    ("smote", SMOTE(random_state=42)),
    ("clf", RandomForestClassifier(n_estimators=400, random_state=42)),
])
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
```

Using `imblearn.pipeline.Pipeline` is what keeps SMOTE inside each fold. If you call
`SMOTE().fit_resample(X, y)` on the whole dataset before splitting, every number you report
is wrong. This is the single most common mistake in student ML projects.

### 2.2 Metrics to compute

```python
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             precision_recall_fscore_support, confusion_matrix,
                             brier_score_loss)
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
```

Report, per model and per week: Accuracy, Precision, Recall, F1, ROC-AUC,
PR-AUC (`average_precision_score`), Brier score, and the confusion matrix.

### 2.3 Threshold selection

Default `0.5` is arbitrary. Missing an at-risk student costs far more than a false alarm:

```python
import numpy as np
probs = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
best = max(((t, 5*recall_at(t) + 1*precision_at(t)) for t in np.arange(0.1, 0.9, 0.01)),
           key=lambda p: p[1])
```

Say out loud in the review: "we weighted recall 5× because a missed at-risk student is
five times worse than an unnecessary counselling session."

### 2.4 Deliverable

`models/model.joblib`, `models/threshold.json`, and a results table saved as CSV.

---

## Phase 3 — SHAP (week 5)

```python
import shap
explainer = shap.TreeExplainer(model)
sv = explainer(X_test)

shap.plots.beeswarm(sv)          # global — which factors drive risk overall
shap.plots.waterfall(sv[0])      # local  — why THIS student is at risk
```

Save `explainer` with joblib so the API doesn't rebuild it per request.

**Stability check (part of contribution c):** compute the top-5 features by
mean |SHAP|, by LIME, and by `permutation_importance`. Report the Jaccard overlap
between the three sets. A number like "0.6 overlap between SHAP and LIME"
is a real, reportable result.

---

## Phase 4 — Counterfactual recourse (week 6) — the novelty

```python
import dice_ml
from dice_ml import Dice

d = dice_ml.Data(dataframe=train_df, continuous_features=["absences", "studytime", "G1"],
                 outcome_name="at_risk")
m = dice_ml.Model(model=model, backend="sklearn")
exp = Dice(d, m, method="random")

cf = exp.generate_counterfactuals(
    query_instances=student_row,
    total_CFs=3,
    desired_class=0,                                  # move them to NOT at-risk
    features_to_vary=["absences", "studytime",
                      "assignment_submitted", "schoolsup"],   # only actionable ones
    permitted_range={"absences": [0, 8], "studytime": [2, 4]} # only feasible changes
)
cf.visualize_as_dataframe()
```

The two arguments that make this a contribution rather than a demo are
`features_to_vary` and `permitted_range`. Without them DiCE will happily suggest
"change your father's education level" — which is why you must freeze immutables.

Then convert the raw counterfactual into text:

```python
def to_action_plan(original, counterfactual):
    steps = []
    for col in counterfactual.index:
        if original[col] != counterfactual[col]:
            steps.append(f"{LABELS[col]}: {original[col]} → {counterfactual[col]}")
    return steps
```

**Report three recourse metrics:** validity (% of counterfactuals that actually flip
the prediction when fed back to the model), proximity (mean number of features changed),
feasibility (% that respect the permitted ranges).

---

## Phase 5 — Earliness experiment (can run alongside phase 4)

Train the same pipeline on week-4, week-8 and week-12 feature sets. Plot recall
(y-axis) against prediction week (x-axis). One chart, one paragraph — and it is the
result the panel will remember, because it answers a question the base paper doesn't ask.

---

## Phase 6 — API (weeks 7–8)

```python
# src/api/main.py
from fastapi import FastAPI, Depends
import joblib

app = FastAPI(title="EduSight API")
model = joblib.load("models/model.joblib")          # loaded ONCE at import
explainer = joblib.load("models/explainer.joblib")

@app.post("/predict")
def predict(student: StudentIn):
    ...

@app.post("/explain")
def explain(student: StudentIn):
    ...   # returns top SHAP contributions as {feature, value, shap_value}

@app.post("/recommend")
def recommend(student: StudentIn):
    ...   # returns the action plan steps

@app.get("/cohort")
def cohort(user=Depends(require_role("faculty"))):
    ...   # class-level summary
```

Run with `uvicorn src.api.main:app --reload`, test every endpoint in the
auto-generated docs at `http://localhost:8000/docs` before writing any frontend code.

**Auth (M6):** `python-jose` for JWT, `passlib[bcrypt]` for passwords, a
`require_role("student"|"faculty")` dependency, and an explicit check that
`student_id in token == student_id in request` on `/predict`, `/explain`, `/recommend`.

---

## Phase 7 — Dashboards (weeks 9–10)

```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install axios recharts
```

**Student dashboard:** risk badge (green/amber/red), a horizontal bar chart of the top-5
SHAP contributions, and the action plan as a checklist with target values.

**Teacher dashboard:** a stacked bar of risk bands per class, a bar chart of the most
common risk drivers, and a sortable table of students ordered by risk.

Keep it plain. A clean, working two-page dashboard beats a half-finished pretty one.

---

## Phase 8 — Experiments, report, demo (weeks 11–12)

- Fairness check: compare false-negative rate across `sex` and `address` (urban/rural)
  subgroups. One table.
- Final results table: every model × every week × every metric.
- Record a 3-minute demo video as backup in case the live demo fails at the review.

---

## Working with AI agents — how to get good output

You said you'll use AI agents. That works well here **if you drive them file by file.**

**Do this:**

1. Give the agent `src/config.py` and the feature manifest as context in every session.
   Most bad agent output comes from the agent inventing column names.
2. Ask for **one file at a time**, with the exact function signatures you want:
   *"Write `src/recourse.py` with a function `generate_plan(student_dict) -> list[str]`
   that uses dice-ml, freezes these columns [...], and returns plain-language steps.
   Do not write a main block."*
3. **Run every file the moment it's generated.** Don't accumulate five unrun files.
4. After each phase, ask the agent to write the tests, then check the tests yourself.
5. Keep the notebooks as ground truth. If `src/train.py` and `02_baseline_models.ipynb`
   disagree on a number, stop and find out why before moving on.

**Do not do this:**

- "Build me the whole EduSight project." You will get plausible code that doesn't run
  against your data and that you can't defend in the viva.
- Accept metric numbers the agent writes into a report. Only report numbers you produced
  by running code yourself.
- Let the agent pick the dataset columns or the target definition. Those are your
  design decisions and they are what the panel questions.

**The viva test:** for every file in `src/`, you should be able to explain what it does
and why in two sentences without looking at it. If you can't, you don't own that file yet
— read it line by line before moving on. This matters more than any other advice here,
because the examiner's questions go to you, not the agent.

---

## Pitfall checklist — check before every review

- [ ] `G3` is not in the feature list anywhere.
- [ ] SMOTE sits inside the CV pipeline, never applied to the full dataset.
- [ ] Confusion matrix is shown next to every accuracy figure.
- [ ] The decision threshold is stated and justified, not left at 0.5.
- [ ] Counterfactuals only vary actionable features, and validity is reported.
- [ ] The model is loaded once at API start-up, not per request.
- [ ] No student can query another student's ID.
- [ ] Every number in the slides was produced by code you ran.
- [ ] Every reference in the deck has been opened and confirmed to exist.

---

## This week's three tasks

1. Create the repo, `pip install -r requirements.txt`, download `student-por.csv`.
2. Write `src/config.py` with the three feature lists (week 4 / 8 / 12) and the target rule.
3. Run one Random Forest with `StratifiedKFold` and print the confusion matrix.

Once that prints, everything after it is incremental.
