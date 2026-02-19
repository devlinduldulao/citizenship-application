# Phase 1 (A) — Hackathon Ready ✅ Completed

> **Status: Completed** — This phase covers the current MVP as shipped. All items below are implemented and working.

## Leadership One-Page

| Item | Summary |
|------|---------|
| Status | Completed and currently shipping |
| Business outcome | Manual-review throughput improved with explainability, queue prioritization, and auditable decisions |
| Scope delivered | Intake + OCR/NLP + rule scoring + reviewer decisions + queue/SLA + 2 AI assist endpoints |
| Operational confidence | High (existing tests, linting, and dockerized runtime) |
| Estimated effort | N/A (already delivered) |
| Mandatory cost | $0 |
| Recommendation | Confirm baseline and proceed to Phase 2 (Reviewer Copilot) |

### Leadership sign-off criteria

- Baseline APIs respond correctly in dev
- Frontend applications workflow shows explainability and AI panels
- Audit trail and queue metrics are visible for superusers

## Cross-Phase Index

Use this as the quick navigation map for review:

| Phase | Focus | Status | Effort | Link |
|------|-------|--------|--------|------|
| 1 (A) | Hackathon Ready baseline | Completed | — | [phase_1.md](phase_1.md) |
| 2 (B) | Reviewer Copilot | Not started | ~13–19 hours | [phase_2.md](phase_2.md) |
| 3 (C) | Predictive Operations | Not started | ~15–22 hours | [phase_3.md](phase_3.md) |
| 4 (D+E) | Policy + Governance hardening | Not started | ~55–85 hours | [phase_4.md](phase_4.md) |

Recommended reading order for decision-makers: Phase 1 → Phase 2 → Phase 3 → Phase 4.

## Tech Lead Snapshot

- **Source of truth:** This file + the implemented MVP sections in `README.md`
- **Validation intent:** Treat this as a baseline inventory before approving Phase 2 work
- **Decision gate:** Approve if all listed APIs and UI panels are reachable in local/dev environment

---

## What was delivered

Phase A corresponds to the **MVP scope** described in the project README, covering four implementation milestones plus two AI-assist endpoints.

---

## Milestone 1 — Intake and Processing Pipeline

**What it does:** Standardized application creation, document upload, and background processing with real OCR + NLP extraction.

### Implemented

- [x] `CitizenshipApplication` CRUD (create, read, update, list)
- [x] `ApplicationDocument` upload endpoint (PDF/image, any document type)
- [x] Background processing pipeline: `queued → processing → review_ready`
- [x] OCR extraction via PyMuPDF (digital PDFs) with Tesseract fallback (scanned/images)
- [x] NLP entity extraction: dates, passport numbers, nationalities, names, addresses, keywords, language/residency indicators
- [x] Hybrid spaCy (Norwegian `nb_core_news_sm`) + regex NLP pipeline
- [x] Structured `extracted_fields` and `ocr_text` stored per document
- [x] Graceful degradation when Tesseract or spaCy are unavailable

### Key files

| File | Purpose |
|------|---------|
| `backend/app/models.py` | `CitizenshipApplication`, `ApplicationDocument` models |
| `backend/app/api/routes/applications.py` | CRUD + upload + processing endpoints |
| `backend/app/services/ocr.py` | PyMuPDF + Tesseract OCR extraction |
| `backend/app/services/nlp.py` | Regex + spaCy entity extraction |
| `backend/app/crud.py` | Database operations |

---

## Milestone 2 — Explainable Eligibility Engine

**What it does:** Deterministic weighted rule engine that scores each application with transparent rationale.

### Implemented

- [x] 7 weighted eligibility rules (identity, residency, document quality, language, security, entity richness, residency duration)
- [x] Confidence score (0–1) and risk level (`low`, `medium`, `high`) per application
- [x] Rule-by-rule rationale and evidence payload
- [x] `GET /{id}/decision-breakdown` endpoint returning full rule results
- [x] NLP-enhanced scoring (passport numbers, residency keywords, language indicators boost relevant rules)

### Key files

| File | Purpose |
|------|---------|
| `backend/app/models.py` | `EligibilityRuleResult` model |
| `backend/app/api/routes/applications.py` | Decision breakdown endpoint |
| `frontend/src/routes/_layout/applications.tsx` | Explainability panel UI |

---

## Milestone 3 — Human-in-the-Loop Decisioning

**What it does:** Caseworker review actions with mandatory reasoning and immutable audit trail.

### Implemented

- [x] Superuser review actions: `approve`, `reject`, `request_more_info`
- [x] Mandatory decision reason capture (8–1000 chars)
- [x] `POST /{id}/review-decision` endpoint
- [x] `ApplicationAuditEvent` model with immutable event log
- [x] `GET /{id}/audit-trail` endpoint
- [x] Audit trail UI timeline in frontend
- [x] Status transitions enforced: `review_ready → approved | rejected | more_info_required`

### Key files

| File | Purpose |
|------|---------|
| `backend/app/models.py` | `ApplicationAuditEvent`, `ReviewDecisionRequest` models |
| `backend/app/api/routes/applications.py` | Review decision + audit trail endpoints |
| `frontend/src/routes/_layout/applications.tsx` | Decision UI + audit timeline |

---

## Milestone 4 — Reviewer Queue and SLA Management

**What it does:** Priority scoring, SLA tracking, and operational metrics for the manual review backlog.

### Implemented

- [x] `priority_score` (0–100) on each application
- [x] `sla_due_at` date assignment for pending manual decisions
- [x] `GET /queue/review` — prioritized queue with overdue indicators (superuser only)
- [x] `GET /queue/metrics` — aggregate workload metrics (pending, overdue, high-priority counts)
- [x] `is_overdue` computed flag on queue items

---

## AI-Assist Endpoints (Phase A capstone)

**What it does:** Two AI-powered advisory endpoints surfaced directly in the application workflow UI.

### Implemented

- [x] `GET /{id}/case-explainer` — decision memo with summary, recommended action, key risks, missing evidence, next steps
- [x] `GET /{id}/evidence-recommendations` — targeted missing-document suggestions with rationale
- [x] Optional LLM generation via any OpenAI-compatible API (`AI_EXPLAINER_BASE_URL`)
- [x] Deterministic rules-based fallback when no LLM is configured
- [x] Frontend cards: "AI Case Explainer" and "AI Evidence Recommendations" in application detail view

### Key files

| File | Purpose |
|------|---------|
| `backend/app/services/case_explainer.py` | LLM + fallback case explanation and evidence recommendations |
| `backend/app/core/config.py` | `AI_EXPLAINER_*` settings |
| `frontend/src/routes/_layout/applications.tsx` | AI Insights UI cards |

---

## Infrastructure (in place)

- [x] FastAPI + SQLModel + PostgreSQL backend
- [x] React 19 + Vite + TanStack Router/Query frontend
- [x] Auto-generated frontend SDK from OpenAPI spec (Hey API)
- [x] JWT authentication (Argon2/bcrypt password hashing)
- [x] Docker Compose orchestration with Traefik
- [x] Pytest backend tests + Vitest frontend unit tests
- [x] Ruff (backend) + Biome (frontend) linting
- [x] Alembic database migrations

---

## Summary

Everything in this file is **already shipping**. Phases 2 through 4 build on top of this foundation.

### Baseline verification checklist

- [ ] `GET /api/v1/applications/{application_id}/case-explainer` returns 200 for a valid app
- [ ] `GET /api/v1/applications/{application_id}/evidence-recommendations` returns 200 for a valid app
- [ ] Applications UI shows both AI cards (Case Explainer + Evidence Recommendations)
- [ ] Review queue endpoint and metrics endpoint both return data for superuser
- [ ] Audit trail endpoint returns chronological event history

---

## Approval Sign-Off

| Field | Value |
|------|-------|
| Phase | 1 (A) — Hackathon Ready |
| Version | v1.0 |
| Last Updated | 2026-02-19 |
| Owner | |
| Reviewer | |
| Review Date | |
| Decision | Pending / Approved / Changes Requested |
| Notes | |
