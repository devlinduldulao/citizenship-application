# Phase 2 (B) — Reviewer Copilot

> **Status: Not Started** — Next phase. Adds contextual Q&A for reviewers, grounded in rules, documents, and audit trail, with strict citation payloads.

Back to index: [Phase Overview](phase_1.md#cross-phase-index)

## Leadership One-Page

| Item | Summary |
|------|---------|
| Status | Not started |
| Objective | Deliver reviewer copilot Q&A with citation-first traceability |
| Delivery approach | 2 slices: must-have first, LLM enhancements second |
| Estimated effort | ~13–19 engineering hours |
| Mandatory cost | $0 |
| Primary risk | Citation quality/hallucination if LLM output is not validated |
| Risk control | Deterministic fallback + citation source-id validation |
| Recommendation | Go (low integration risk, high reviewer value) |

### Leadership decision points

- Approve Slice 1 as mandatory deliverable for next increment
- Treat Slice 2 as optional enhancement if schedule remains
- Require audit-event logging and fallback behavior before release

### Presentation quick summary

- Reviewer-facing value appears in the next increment with Slice 1
- Delivery is low-risk because it reuses existing endpoints, models, and UI patterns
- Strong fallback strategy prevents external API dependency risk

---

## Goal

Give reviewers a copilot they can ask questions about any application — "Why this risk level?", "Which rules failed?", "What document would help most?" — and get cited, traceable answers. Works fully without any paid LLM (deterministic fallback), with optional LLM enhancement using the existing `AI_EXPLAINER_*` config.

## Priority real-world use case (must include)

**Scenario:** Applicant has a new passport, old passport (historical 10-year evidence) is lost, and the case enters manual review with long wait and low transparency.

### Product requirements for this scenario

- Copilot must answer: **"Why is this case in manual review?"** with explicit reason codes and cited evidence.
- Copilot must answer: **"What can substitute for a lost old passport?"** with policy-aligned alternatives (for example, police loss report, embassy confirmation, historical permit IDs, travel history records).
- System must distinguish **"missing required document"** vs **"missing but explained with acceptable substitute"**.
- Reviewer panel must show a short **next-action checklist** so caseworkers can resolve blockers faster.

### Applicant transparency companion (recommended in same release)

Add a lightweight applicant-facing status summary endpoint:

`GET /api/v1/applications/{application_id}/review-status-summary`

Response fields:

- `manual_review_reason_codes: list[str]`
- `missing_or_substitute_evidence: list[str]`
- `latest_review_stage: str`
- `updated_at: datetime`

This does not expose sensitive internal notes; it only provides actionable, non-sensitive guidance so applicants know what is blocking progress.

## Cost

- **$0 required** — deterministic fallback answers all three target questions without any LLM
- **Optional:** any OpenAI-compatible API for richer answers. Free options: Ollama (local), LM Studio (local), Groq (free tier). Cheap option: GPT-4.1-mini (~$0.40/M input tokens)
- No new tools, licenses, or SaaS subscriptions needed
- No new pip/npm packages needed
- No database migrations needed

## Phase 2 MVP cut line (recommended)

Ship in two slices so reviewers get value quickly:

- **Slice 1 (must-have):** backend endpoint + deterministic fallback + citations + minimal frontend panel
- **Slice 2 (enhancement):** optional LLM answers, richer chat UX polish, expanded test matrix

If timeline is tight, merge after Slice 1 and defer Slice 2.

## Dependencies and sequencing

- **Hard dependency:** OpenAPI/SDK regeneration after backend endpoint merge
- **Soft dependency:** Existing AI cards in applications UI (already present)
- **No migration dependency:** No schema changes required for initial rollout

---

## Step 1 — Add Pydantic response models

**File:** `backend/app/models.py` (edit existing)

Add three new schemas alongside `ApplicationCaseExplanationPublic`:

```python
class CopilotCitationPublic(SQLModel):
    """One traceable source reference backing a copilot claim."""
    source_type: str       # "rule" | "document" | "audit_event"
    source_id: str         # UUID of the referenced rule/document/event
    source_label: str      # Human-readable label (rule_code, document_type, event action)
    excerpt: str           # The specific detail cited

class CopilotAnswerPublic(SQLModel):
    """Structured response from the Reviewer Copilot Q&A."""
    application_id: uuid.UUID
    question: str
    answer: str
    citations: list[CopilotCitationPublic]
    confidence: str        # "high" | "medium" | "low"
    generated_by: str      # "llm:<model>" or "fallback:copilot-qa-v1"
    generated_at: datetime | None = None

class CopilotQuestionRequest(SQLModel):
    """Incoming question from a reviewer."""
    question: str = Field(min_length=5, max_length=500)
```

**Why:** `citations[]` with `source_type` + `source_id` lets the frontend link each claim back to the exact rule, document, or audit event — fulfilling the ROADMAP requirement for strict citation payloads.

---

## Step 2 — Build the copilot Q&A service

**File:** `backend/app/services/copilot_qa.py` (new file)

### 2a. Context assembly

Reuse the pattern from `_request_llm_explanation()` in `case_explainer.py`:

```python
def _assemble_copilot_context(application, rules, documents, audit_events, risk_level) -> dict:
```

- Packs application summary, rule results, document metadata (type, status, OCR text snippets), and recent audit events into a single dict
- Adds `source_id` (UUID as string) to every item so the LLM can reference them in citations
- Caps OCR text at 500 chars per document, limits to 10 most recent audit events

### 2b. Deterministic fallback (works with zero LLM)

```python
def _answer_without_llm(question, application, rules, documents, audit_events, risk_level) -> dict:
```

Pattern-match the question against three target intents using simple keyword matching:

| Keywords in question | Handler |
|---|---|
| `risk`, `level`, `why risk` | **Q1:** Return failed rules sorted by weight, explain risk level derivation |
| `rule`, `failed`, `eligibility` | **Q2:** List all failed `EligibilityRuleResult` with rationale |
| `document`, `evidence`, `improve`, `confidence`, `upload` | **Q3:** Reuse `generate_evidence_recommendations()` logic |
| No match | Generic case summary (reuse `_build_fallback_explanation()` output) |

Each answer includes proper `citations[]` referencing the specific rules/documents that support it.

### 2c. LLM-backed function (optional, uses existing config)

```python
def _answer_with_llm(question, context, model, api_key, base_url, temperature, timeout) -> dict:
```

- Sends chat completion to the configured OpenAI-compatible API (same `AI_EXPLAINER_*` settings)
- System prompt enforces strict JSON with `answer`, `citations[]`, `confidence`
- Citation validation: strips any citation whose `source_id` isn't in the provided context
- Falls back to deterministic answer on any error (timeout, parse failure, etc.)

### 2d. Main entry point

```python
def generate_copilot_answer(question, application, rules, documents, audit_events, risk_level) -> dict:
```

- LLM enabled → try `_answer_with_llm()`, fall back on error
- LLM not enabled → use `_answer_without_llm()`
- Always returns a well-formed dict matching `CopilotAnswerPublic`

---

## Step 3 — Add the API endpoint

**File:** `backend/app/api/routes/applications.py` (edit existing)

```
POST /api/v1/applications/{application_id}/copilot-qa
```

- **Request body:** `CopilotQuestionRequest` (5–500 chars)
- **Response:** `CopilotAnswerPublic`
- **Auth:** same `CurrentUser` dependency as existing endpoints
- **Logic:**
  1. Load application via `get_owned_application()`
  2. Load rules, documents, audit_events (same queries as case-explainer endpoint)
  3. Compute `risk_level` from `confidence_score`
  4. Call `generate_copilot_answer()`
  5. Log audit event: `action="copilot_qa_asked"`, store `question` + `generated_by` in `event_metadata`
  6. Return `CopilotAnswerPublic`

---

## Step 4 — Build the frontend copilot panel

**File:** `frontend/src/components/Copilot/CopilotPanel.tsx` (new file)
**File:** `frontend/src/components/Copilot/CitationBadge.tsx` (new file)

### CopilotPanel component

A chat-style card in the application detail view:

```
┌──────────────────────────────────────────┐
│  🤖 Reviewer Copilot                     │
│──────────────────────────────────────────│
│  Quick questions:                        │
│  [Why this risk level?]                  │
│  [Which rules failed?]                   │
│  [Best document to upload?]              │
│                                          │
│  Q: Why is this application medium risk? │
│  A: 2 of 5 rules failed. The most       │
│     impactful gap is residency...        │
│     📎 residency_evidence [rule]         │
│     📎 language_requirement [rule]       │
│     Confidence: medium                   │
│──────────────────────────────────────────│
│  [Ask a question...            ] [Send]  │
└──────────────────────────────────────────┘
```

- Three quick-ask buttons for the canonical questions
- Scrollable conversation history (local state, resets on application change)
- `useMutation` for the POST call (same pattern as review decision)
- Loading spinner while waiting, inline error on failure

### CitationBadge component

- Renders `[📄 passport]`, `[⚖️ identity_document_present]`, or `[📋 status_changed]`
- Uses existing `Badge` component with `variant="outline"`
- Tooltip shows the `excerpt` text

### Integration

**File:** `frontend/src/routes/_layout/applications.tsx` (edit existing)

- Import and render `<CopilotPanel>` between the existing AI cards
- Conditional on `selectedApplicationId` (same pattern as other cards)
- Uses `key={selectedApplicationId}` to reset conversation when switching applications

---

## Step 5 — Regenerate frontend SDK

```bash
cd backend && uv run fastapi dev app/main.py   # Start backend
cd frontend && bun run generate-client           # Regenerate TypeScript types
```

The new `CopilotAnswerPublic`, `CopilotCitationPublic`, and `CopilotQuestionRequest` types are auto-generated.

---

## Step 6 — Tests

### Backend service tests (`backend/tests/services/test_copilot_qa.py`)

| Test | Verifies |
|------|----------|
| `test_fallback_why_risk_level` | Q1 handler returns answer + rule citations |
| `test_fallback_which_rules_failed` | Q2 handler lists failed rules |
| `test_fallback_best_document` | Q3 handler recommends evidence type |
| `test_fallback_generic_question` | Unrecognized question returns case summary |
| `test_citation_validation_strips_invalid` | Hallucinated source_ids removed |
| `test_citation_validation_downgrades_confidence` | All citations stripped → confidence = "low" |
| `test_llm_invalid_json_falls_back` | Bad LLM output triggers fallback |
| `test_llm_disabled_uses_fallback` | No API key → always deterministic |
| `test_lost_old_passport_substitute_guidance` | Copilot returns substitute evidence guidance for lost historical passport scenario |

### Backend API tests (`backend/tests/api/routes/test_copilot_qa.py`)

| Test | Verifies |
|------|----------|
| `test_copilot_qa_success` | POST returns 200 with valid schema |
| `test_copilot_qa_creates_audit_event` | Audit event logged with `action="copilot_qa_asked"` |
| `test_copilot_qa_question_validation` | Too short/long questions return 422 |
| `test_copilot_qa_unauthorized` | No auth → 401 |
| `test_review_status_summary_masks_sensitive_notes` | Applicant summary endpoint returns actionable status without exposing internal reviewer-only notes |

### Frontend component tests (`frontend/src/tests/copilot-panel.test.tsx`)

| Test | Verifies |
|------|----------|
| `renders quick-ask buttons` | Three preset buttons visible |
| `submits question and shows answer` | Mock API, verify answer renders |
| `displays citation badges` | Badges appear with correct labels |
| `shows loading state` | Spinner visible while pending |

---

## Files changed/created summary

| File | Action | What |
|------|--------|------|
| `backend/app/models.py` | Edit | Add 3 Pydantic models |
| `backend/app/services/copilot_qa.py` | Create | Q&A service with fallback + LLM |
| `backend/app/api/routes/applications.py` | Edit | Add POST copilot-qa endpoint |
| `frontend/src/components/Copilot/CopilotPanel.tsx` | Create | Copilot chat panel |
| `frontend/src/components/Copilot/CitationBadge.tsx` | Create | Citation badge component |
| `frontend/src/routes/_layout/applications.tsx` | Edit | Integrate copilot panel |
| `frontend/src/client/*` | Regenerate | Auto-generated SDK types |
| `backend/tests/services/test_copilot_qa.py` | Create | Service unit tests |
| `backend/tests/api/routes/test_copilot_qa.py` | Create | API route tests |
| `frontend/src/tests/copilot-panel.test.tsx` | Create | Component tests |

## Estimated effort

- **~13–19 hours** total for an engineer familiar with the codebase
- No new dependencies, migrations, environment variables, or infrastructure changes

## Go/No-Go acceptance criteria

- [ ] Copilot endpoint returns cited responses for all 3 canonical questions
- [ ] Fallback works when `AI_EXPLAINER_API_KEY` is unset
- [ ] Citations never reference unknown `source_id` values
- [ ] Frontend panel handles loading, error, and success states cleanly
- [ ] Audit event `copilot_qa_asked` is persisted per request
- [ ] Lost historical passport scenario returns substitute-evidence guidance and reason-coded explanation

---

## Approval Sign-Off

| Field | Value |
|------|-------|
| Phase | 2 (B) — Reviewer Copilot |
| Version | v1.0 |
| Last Updated | 2026-02-19 |
| Owner | |
| Reviewer | |
| Review Date | |
| Decision | Pending / Approved / Changes Requested |
| Notes | |
