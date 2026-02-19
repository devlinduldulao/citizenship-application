# Phase 4 (D+E) — Policy Intelligence + Governance & Production Hardening

> **Status: NOT STARTED** — Mid-term phase. Expands deterministic rule coverage, adds versioned rule sets, simulation mode, model monitoring, audit lineage, and access controls.

---

## Goal

Two complementary objectives combined into one phase:

1. **Policy Intelligence (D):** Make the rule engine production-grade for legal compliance — versioned rules, wider coverage, reproducible decisions, and a simulation mode for training and impact analysis.
2. **Governance & Hardening (E):** Add operational safeguards — model monitoring, prompt/version lineage in audit trails, and governance workflows for configuration changes.

## Cost

- **$0 for all core work** — no external services needed
- Everything runs on existing PostgreSQL + FastAPI stack
- Optional: Prometheus/Grafana for monitoring dashboards (both free and open-source)

## Prerequisites

- Phase 1 (A) completed: eligibility rules and audit events working
- Phase 2 (B) completed: copilot Q&A with citation payloads
- Phase 3 (C) recommended but not strictly required

---

# Part 1: Policy Intelligence (D)

---

## Step 1 — Expand deterministic rule coverage

**File:** `backend/app/services/nlp.py` (edit existing)
**File:** `backend/app/api/routes/applications.py` (edit existing — rule evaluation logic)

### New rule packs to add

Expand beyond the current 7 rules to cover more legal requirements:

| Rule pack | New rules | Weight range |
|-----------|-----------|-------------|
| **Financial** | Tax history present, income documentation, self-sufficiency evidence | 0.10–0.15 |
| **Criminal record** | Criminal record check present, no disqualifying convictions signal | 0.10–0.15 |
| **Residency duration** | Minimum 7 years residency documentation, continuous stay evidence | 0.10–0.18 |
| **Citizenship renunciation** | Evidence of prior citizenship renunciation intent/process | 0.05–0.10 |
| **Age/exemption** | Age-based exemptions (under 18, over 67), Nordic fast-track signals | 0.05–0.10 |

### NLP enhancements for new rules

Add regex patterns to `nlp.py` for:
- Tax-related keywords: `skatteattest`, `ligningsattest`, `skattemelding`
- Criminal record terms: `vandelsattest`, `strafferegister`, `politiattest`
- Renunciation terms: `løsning fra statsborgerskap`, `frasigelse`
- Duration indicators: year ranges, `sammenhengende`, `uavbrutt opphold`

---

## Step 2 — Versioned rule sets

**File:** `backend/app/models.py` (edit existing)

### New model: `RuleSetVersion`

```python
class RuleSetVersion(SQLModel, table=True):
    __tablename__ = "rule_set_version"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    version_label: str = Field(max_length=32)      # e.g. "v1.0", "v2.1"
    description: str = Field(max_length=500)        # What changed in this version
    rules_config: dict[str, Any] = Field(sa_type=JSON)  # Full rule definitions (code, weight, logic ref)
    is_active: bool = Field(default=False)           # Only one version active at a time
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))
    created_by_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")
```

### Changes to existing models

- Add `rule_set_version_id` to `EligibilityRuleResult` — links each result to the version used
- Add `rule_set_version_id` to `CitizenshipApplication` — records which version was active at decision time

### Decision reproducibility

When reviewing a past decision:
1. Load the `rule_set_version_id` stored on the application
2. Re-evaluate using that version's `rules_config`
3. Confirm results match — if not, flag for investigation

**Database migration required:** `alembic revision --autogenerate -m "add rule set versioning"`

---

## Step 3 — Rule management API

**File:** `backend/app/api/routes/rules.py` (new file)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/rules/versions` | GET | List all rule set versions |
| `/api/v1/rules/versions` | POST | Create new rule set version (superuser only) |
| `/api/v1/rules/versions/{id}/activate` | POST | Activate a version (superuser only, deactivates current) |
| `/api/v1/rules/versions/{id}` | GET | Get specific version with full config |

All version changes logged as audit events.

---

## Step 4 — Simulation mode

**File:** `backend/app/services/simulator.py` (new file)

### Purpose

Two use cases:
1. **Caseworker training:** Run "what if" scenarios on sample applications without affecting real data
2. **Policy impact analysis:** Preview how a rule change would affect existing applications

### Simulation endpoint

```
POST /api/v1/rules/simulate
```

**Request body:**

```python
class SimulationRequest(SQLModel):
    rules_config: dict[str, Any]       # Custom rule definitions to test
    application_ids: list[uuid.UUID]   # Which applications to re-evaluate (max 50)
```

**Response:**

```python
class SimulationResultPublic(SQLModel):
    results: list[SimulationApplicationResult]
    summary: SimulationSummary

class SimulationApplicationResult(SQLModel):
    application_id: uuid.UUID
    original_confidence: float
    simulated_confidence: float
    original_risk_level: str
    simulated_risk_level: str
    changed_rules: list[str]           # Which rules produced different results

class SimulationSummary(SQLModel):
    total_applications: int
    risk_level_changes: dict[str, int]  # e.g. {"low→medium": 3, "medium→high": 1}
    avg_confidence_delta: float
```

- Read-only: no database writes, no status changes
- Superuser only
- Logged as audit event: `action="simulation_run"`

---

# Part 2: Governance & Production Hardening (E)

---

## Step 5 — Model and prompt monitoring

**File:** `backend/app/services/monitoring.py` (new file)

### What to monitor

| Metric | How | Why |
|--------|-----|-----|
| LLM response latency | Record `time.perf_counter()` around API calls | Detect slowdowns |
| LLM error rate | Count exceptions in `_request_llm_explanation()` and `_answer_with_llm()` | Detect provider issues |
| Fallback rate | Count how often fallback is used vs LLM | Track LLM reliability |
| Citation validity rate | Count stripped citations vs total | Detect prompt degradation |
| Confidence distribution | Histogram of `confidence_score` over time | Detect drift in scoring |

### Implementation approach

1. Add a `ModelMetricsCollector` class that records metrics to a `model_metrics` database table
2. Add a `GET /api/v1/admin/model-metrics` endpoint (superuser only) returning aggregated metrics
3. Optional: expose Prometheus-format metrics at `/metrics` for Grafana dashboards

**Database migration required:** `alembic revision --autogenerate -m "add model metrics table"`

---

## Step 6 — Prompt and version lineage in audit events

**File:** `backend/app/services/case_explainer.py` (edit existing)
**File:** `backend/app/services/copilot_qa.py` (edit existing — from Phase 2)

### Changes

Every AI-generated output now records in its audit event:

```python
metadata = {
    "prompt_version": "case-explainer-v1.2",    # Track prompt template version
    "model": settings.AI_EXPLAINER_MODEL,         # Which model was used
    "temperature": settings.AI_EXPLAINER_TEMPERATURE,
    "rule_set_version": active_rule_set.version_label,
    "generated_by": "llm:gpt-4.1-mini" or "fallback:rules-v1",
    "input_token_estimate": len(context_json) // 4,
    "response_latency_ms": elapsed_ms,
}
```

This enables:
- Full reproducibility: re-run the same prompt + model + rules and compare results
- Accountability: every AI output traceable to a specific prompt version and model
- Debugging: if outputs degrade, pinpoint when the prompt or model changed

---

## Step 7 — Access controls and governance workflows

### 7a. Role-based action controls

**File:** `backend/app/models.py` (edit existing)

Extend the user model with finer-grained roles:

```python
class UserRole(str, Enum):
    APPLICANT = "applicant"           # Can submit/view own applications
    REVIEWER = "reviewer"             # Can view queue, make decisions
    ADMIN = "admin"                   # Can manage users, rules, view metrics
    SUPER_ADMIN = "super_admin"       # Can change model config, activate rule versions
```

Currently the system uses `is_superuser` boolean. Migrate to role-based access:

| Action | Required role |
|--------|--------------|
| Submit application | `applicant` or above |
| View review queue | `reviewer` or above |
| Submit review decision | `reviewer` or above |
| Create rule set version | `admin` or above |
| Activate rule set version | `super_admin` only |
| Change AI model configuration | `super_admin` only |
| View model metrics | `admin` or above |
| Run simulation | `admin` or above |

### 7b. Configuration change approval workflow

**File:** `backend/app/services/governance.py` (new file)

For high-impact changes (activating a new rule set, changing LLM model/temperature):

1. Requester creates a `ConfigChangeRequest`
2. A different `super_admin` must approve before it takes effect
3. Both request and approval logged as audit events
4. Provides four-eyes principle for critical configuration

```python
class ConfigChangeRequest(SQLModel, table=True):
    __tablename__ = "config_change_request"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    change_type: str           # "rule_version_activation", "model_config_change"
    change_payload: dict       # The proposed configuration
    status: str                # "pending", "approved", "rejected"
    requested_by_id: uuid.UUID
    approved_by_id: uuid.UUID | None = None
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    resolved_at: datetime | None = None
```

**Database migration required:** `alembic revision --autogenerate -m "add governance tables"`

---

## Step 8 — Frontend governance pages

### Admin model metrics dashboard

**File:** `frontend/src/routes/_layout/admin.tsx` (edit existing) or new route

- Chart showing LLM latency, error rate, fallback rate over time
- Confidence score distribution histogram
- Citation validity rate trend
- Uses existing Card/Badge components, optionally add a chart library (recharts — free, MIT)

### Rule version management page

**File:** `frontend/src/routes/_layout/rules.tsx` (new route)

- List rule set versions with active indicator
- View full rule config for any version
- Create new version (superuser only)
- Activate version with confirmation dialog

### Configuration change requests

**File:** `frontend/src/routes/_layout/governance.tsx` (new route)

- List pending/approved/rejected change requests
- Approve/reject interface for super_admins
- Change history timeline

---

## Files changed/created summary

| File | Action | What |
|------|--------|------|
| **Policy Intelligence (D)** | | |
| `backend/app/models.py` | Edit | `RuleSetVersion`, `SimulationRequest/Result`, extend `EligibilityRuleResult` |
| `backend/app/services/nlp.py` | Edit | New regex patterns for expanded rules |
| `backend/app/api/routes/rules.py` | Create | Rule version management endpoints |
| `backend/app/services/simulator.py` | Create | Simulation engine |
| `backend/app/api/routes/applications.py` | Edit | Expanded rule evaluation, simulation endpoint |
| **Governance & Hardening (E)** | | |
| `backend/app/services/monitoring.py` | Create | Metrics collection service |
| `backend/app/services/governance.py` | Create | Config change request workflow |
| `backend/app/services/case_explainer.py` | Edit | Add prompt/version lineage to audit events |
| `backend/app/services/copilot_qa.py` | Edit | Add prompt/version lineage to audit events |
| `backend/app/models.py` | Edit | `UserRole` enum, `ConfigChangeRequest` model, `ModelMetrics` table |
| `backend/app/api/deps.py` | Edit | Role-based dependency injection |
| `frontend/src/routes/_layout/rules.tsx` | Create | Rule version management page |
| `frontend/src/routes/_layout/governance.tsx` | Create | Config change request page |
| `frontend/src/routes/_layout/admin.tsx` | Edit | Model metrics dashboard |
| **Migrations** | | |
| `backend/app/alembic/versions/` | Create | 2–3 new migration files |

## New dependencies

| Package | Cost | Purpose |
|---------|------|---------|
| `recharts` (frontend, optional) | Free (MIT) | Charts for metrics dashboard |

## Estimated effort

| Part | Work | Hours |
|------|------|-------|
| Expanded rules + NLP patterns | Backend | 8–12 |
| Versioned rule sets + migrations | Backend | 6–10 |
| Simulation mode | Backend + API | 6–8 |
| Model monitoring | Backend | 5–8 |
| Prompt/version lineage | Backend (edit existing) | 3–4 |
| Role-based access controls | Backend | 6–10 |
| Governance workflow | Backend | 5–8 |
| Frontend: metrics + rules + governance pages | Frontend | 10–15 |
| Tests for all above | Both | 8–12 |
| **Total** | | **~55–85 hours** |

---

## Summary across all phases

| Phase | File | Status | Estimated effort |
|-------|------|--------|-----------------|
| 1 (A) — Hackathon Ready | `phase_1.md` | ✅ Completed | — |
| 2 (B) — Reviewer Copilot | `phase_2.md` | Not started | ~13–19 hours |
| 3 (C) — Predictive Operations | `phase_3.md` | Not started | ~15–22 hours |
| 4 (D+E) — Policy + Governance | `phase_4.md` | Not started | ~55–85 hours |
| **Total remaining** | | | **~83–126 hours** |

All phases have **$0 mandatory cost** — every external dependency is free and open-source. Paid LLM APIs are optional enhancements that enhance quality but are never required for functionality.
