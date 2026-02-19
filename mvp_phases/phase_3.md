# Phase 3 (C) — Predictive Operations

> **Status: Not Started** — Short-term phase. Adds lightweight prediction models for triage, SLA risk, and confidence uplift — used only for ranking and queue optimization, never for automatic final decisions.

Back to index: [Phase Overview](phase_1.md#cross-phase-index)

## Leadership One-Page

| Item | Summary |
|------|---------|
| Status | Not started |
| Objective | Add predictive triage signals to improve queue prioritization |
| Estimated effort | ~15–22 engineering hours |
| Mandatory cost | $0 (free/open-source stack) |
| Delivery strategy | Heuristic mode first, trained models only when data gate is met |
| Primary risk | Low historical data causing weak trained-model quality |
| Risk control | Data readiness gate + heuristic-only fallback |
| Recommendation | Conditional Go (start now with heuristic path) |

### Leadership decision points

- Approve heuristic-first rollout regardless of dataset size
- Gate trained-model rollout on minimum data threshold
- Require advisory-only guarantees (no automatic decision mutation)

### Presentation quick summary

- Ships immediate value with heuristic predictors even before model training
- Trained models are intentionally gated to avoid low-data quality issues
- Operational safety is preserved by keeping outputs advisory-only

---

## Goal

Train simple predictive models that help reviewers focus on the right cases first. Three predictions:
1. **Probability of `request_more_info`** — will the reviewer likely need to ask for more documents?
2. **SLA breach risk** — is this case likely to miss its deadline?
3. **Confidence uplift from additional documents** — which missing document class would improve the score the most?

All predictions are advisory only — they inform queue ordering and triage, not decisions.

## Cost

- **$0** — scikit-learn is the only new dependency (free, open-source, already a Python standard)
- No external APIs, no GPU, no cloud ML services
- Models train on the application's own PostgreSQL data (rules, documents, audit events)
- Optional: if the system doesn't have enough historical data yet, ship with heuristic-based predictors first and swap in trained models when data volume is sufficient

## Prerequisites

- Phase 1 (A) completed: application data, rules, documents, audit events all in the database
- Enough historical decisions to train on (recommended: 50+ completed applications for meaningful patterns; heuristic mode works with zero history)

## Data readiness gate (before model training)

Use this gate before green-lighting trained models:

- **Minimum dataset:** 50+ completed applications with final decisions
- **Preferred dataset:** 150+ completed applications with balanced outcomes
- **If gate fails:** ship heuristic predictor only, keep model-training tasks deferred

This keeps delivery predictable and avoids overfitting from sparse data.

---

## Step 1 — Add prediction response models

**File:** `backend/app/models.py` (edit existing)

```python
class TriagePredictionPublic(SQLModel):
    """Predictive triage signals for queue optimization."""
    application_id: uuid.UUID
    more_info_probability: float         # 0–1: likelihood reviewer requests more info
    sla_breach_risk: str                 # "low" | "medium" | "high"
    sla_breach_probability: float        # 0–1
    confidence_uplift_suggestions: list[ConfidenceUpliftSuggestion]
    model_version: str                   # e.g. "heuristic-v1" or "sklearn-v1"
    generated_at: datetime | None = None

class ConfidenceUpliftSuggestion(SQLModel):
    """One document class that would improve confidence if uploaded."""
    document_type: str                   # e.g. "police_clearance"
    estimated_uplift: float              # 0–1: estimated confidence increase
    rationale: str                       # Why this document would help
```

---

## Step 2 — Build the prediction service

**File:** `backend/app/services/triage_predictor.py` (new file)

### 2a. Feature extraction

```python
def _extract_features(application, rules, documents, audit_events) -> dict:
```

Extract features from existing data — no new data collection needed:

| Feature | Source | What it captures |
|---------|--------|-----------------|
| `num_failed_rules` | `EligibilityRuleResult` | How many rules didn't pass |
| `confidence_score` | `CitizenshipApplication` | Current overall score |
| `num_documents` | `ApplicationDocument` | How many docs uploaded |
| `doc_type_coverage` | `ApplicationDocument` | Fraction of expected doc types present |
| `has_police_clearance` | `ApplicationDocument` | Boolean |
| `has_residency_proof` | `ApplicationDocument` | Boolean |
| `has_language_cert` | `ApplicationDocument` | Boolean |
| `avg_nlp_score` | `ApplicationDocument.extracted_fields` | Avg entity richness across docs |
| `days_since_created` | `CitizenshipApplication` | Age of application |
| `days_until_sla` | `CitizenshipApplication` | Time remaining before SLA due |
| `num_status_changes` | `ApplicationAuditEvent` | How many times status changed |
| `has_prior_more_info` | `ApplicationAuditEvent` | Was more info requested before? |

### 2b. Heuristic predictor (ships immediately, no training data needed)

```python
def _predict_heuristic(features: dict) -> dict:
```

Rule-based predictions using feature thresholds:

- **More info probability:** high if `doc_type_coverage < 0.5` or `num_failed_rules >= 3`
- **SLA breach risk:** high if `days_until_sla < 3` and `confidence_score < 0.5`
- **Confidence uplift:** calculate weight of each missing document type's rule, rank by expected score impact

Returns a `TriagePredictionPublic`-shaped dict with `model_version="heuristic-v1"`.

### 2c. Trained predictor (add when data volume is sufficient)

```python
def _predict_trained(features: dict, model) -> dict:
```

- Uses a scikit-learn `RandomForestClassifier` or `GradientBoostingClassifier`
- Trained on historical (features → outcome) pairs from completed applications
- `more_info_probability` = `model.predict_proba()` for the `request_more_info` class
- `sla_breach_risk` = separate classifier trained on SLA miss/hit outcomes

### 2d. Model training script

**File:** `backend/scripts/train_triage_model.py` (new file)

```bash
cd backend && uv run python scripts/train_triage_model.py
```

- Queries all completed applications from the database
- Extracts features, builds labels (`final_decision == "more_info_required"`, `sla_breached`)
- Trains and serializes model to `backend/data/models/triage_model.pkl`
- Prints accuracy, precision, recall metrics
- Designed to be re-run periodically as new data accumulates

### 2e. Main entry point

```python
def generate_triage_prediction(application, rules, documents, audit_events) -> dict:
```

- If trained model exists on disk → use it
- Otherwise → use heuristic predictor
- Always returns valid `TriagePredictionPublic`

---

## Step 3 — Add the API endpoint

**File:** `backend/app/api/routes/applications.py` (edit existing)

```
GET /api/v1/applications/{application_id}/triage-prediction
```

- **Response:** `TriagePredictionPublic`
- **Auth:** superuser only (triage data is operational, not applicant-facing)
- **Logic:**
  1. Load application, rules, documents, audit_events
  2. Call `generate_triage_prediction()`
  3. Return predictions

---

## Step 4 — Integrate predictions into the review queue

**File:** `backend/app/api/routes/applications.py` (edit existing)

Enhance the existing `GET /queue/review` endpoint:

- Add `more_info_probability` and `sla_breach_risk` fields to `ReviewQueueItemPublic`
- Compute predictions for each queued application
- Allow sorting by `more_info_probability` or `sla_breach_risk` (query parameter)

**File:** `backend/app/models.py` (edit existing)

Extend `ReviewQueueItemPublic`:

```python
class ReviewQueueItemPublic(SQLModel):
    # ... existing fields ...
    more_info_probability: float | None = None    # NEW
    sla_breach_risk: str | None = None            # NEW
```

---

## Step 5 — Frontend queue enhancements

**File:** `frontend/src/routes/_layout/applications.tsx` (edit existing)

- Show `more_info_probability` as a colored indicator in the review queue list
- Show `sla_breach_risk` badge next to each queue item
- Add sort/filter controls for triage predictions

**File:** `frontend/src/components/Copilot/TriageBadge.tsx` (new file, optional)

- Visual badge component for prediction risk levels

---

## Step 6 — Tests

### Backend tests

| Test | Verifies |
|------|----------|
| `test_feature_extraction` | All expected features extracted from test data |
| `test_heuristic_more_info_high` | Low doc coverage → high more_info probability |
| `test_heuristic_sla_breach` | Near SLA + low confidence → high breach risk |
| `test_heuristic_confidence_uplift` | Missing doc types ranked by rule weight |
| `test_triage_endpoint_success` | GET returns valid `TriagePredictionPublic` |
| `test_triage_endpoint_superuser_only` | Non-superuser gets 403 |

### Frontend tests

| Test | Verifies |
|------|----------|
| `test_queue_shows_triage_indicators` | Prediction badges render in queue list |

---

## Files changed/created summary

| File | Action | What |
|------|--------|------|
| `backend/app/models.py` | Edit | Add `TriagePredictionPublic`, `ConfidenceUpliftSuggestion`, extend `ReviewQueueItemPublic` |
| `backend/app/services/triage_predictor.py` | Create | Feature extraction + heuristic + trained predictor |
| `backend/scripts/train_triage_model.py` | Create | Model training script |
| `backend/app/api/routes/applications.py` | Edit | Add GET triage-prediction endpoint, enhance queue endpoint |
| `frontend/src/routes/_layout/applications.tsx` | Edit | Show triage indicators in queue |
| `backend/tests/services/test_triage_predictor.py` | Create | Prediction unit tests |
| `backend/tests/api/routes/test_triage.py` | Create | API route tests |

## New dependencies

| Package | Cost | Purpose |
|---------|------|---------|
| `scikit-learn` | Free (BSD) | Classification models for predictions |
| `joblib` | Free (included with scikit-learn) | Model serialization |

Add to `backend/pyproject.toml`:
```toml
[project.optional-dependencies]
ml = ["scikit-learn>=1.5"]
```

## Estimated effort

- **~15–22 hours** total
- Heuristic predictor (ships immediately): ~6–8 hours
- Trained model + training script: ~5–7 hours (can defer until data volume is sufficient)
- Frontend queue enhancements: ~4–7 hours

## Go/No-Go acceptance criteria

- [ ] Queue API still meets current latency expectations after prediction fields are added
- [ ] Prediction outputs are advisory-only and never mutate decision status
- [ ] Heuristic mode works with zero trained model artifacts present
- [ ] If trained mode is enabled, baseline quality metrics are documented (precision/recall)
- [ ] Frontend can sort by prediction fields without breaking existing queue behavior

---

## Approval Sign-Off

| Field | Value |
|------|-------|
| Phase | 3 (C) — Predictive Operations |
| Version | v1.0 |
| Last Updated | 2026-02-19 |
| Owner | |
| Reviewer | |
| Review Date | |
| Decision | Pending / Approved / Changes Requested |
| Notes | |
