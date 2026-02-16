# Norwegian Citizenship Automation MVP

## What this project is about

This project is a **monolithic MVP** that demonstrates how Norway's citizenship application process can be accelerated using automation.

The goal is to reduce manual bottlenecks (currently up to ~2 years waiting time in many cases) by combining:

- document upload and structured case intake,
- OCR/NLP-assisted extraction,
- explainable rule-based eligibility scoring,
- caseworker decision support,
- immutable audit trail for accountability.

The intended audience includes **UDI/Politi stakeholders** who need a practical, demo-ready system that is fast, transparent, and operationally realistic.

## MVP scope (implemented)

### Phase 1 — Intake and processing pipeline

- Citizenship application creation and management
- Requirement document upload (PDF/image)
- Background processing pipeline skeleton for OCR extraction

### Phase 2 — Explainable eligibility engine

- Deterministic weighted rule engine
- Confidence score and risk level per application
- Rule-by-rule rationale and evidence breakdown API
- Frontend explainability panel for reviewers

### Phase 3 — Human-in-the-loop decisioning

- Superuser caseworker decision actions (`approve`, `reject`, `request_more_info`)
- Mandatory decision reason capture
- Immutable audit trail endpoint and UI timeline
- End-to-end tested runtime flow (intake → processing → review decision)

### Phase 4 — Reviewer queue and SLA management

- Priority scoring to rank manual-review workload
- SLA due-date assignment for pending manual decisions
- Admin reviewer queue endpoint with overdue indicators
- Queue metrics endpoint for pending/overdue visibility

## Queue & SLA operations

These APIs support reviewer workload balancing and operational monitoring.

- `GET /api/v1/applications/queue/review` (superuser): returns prioritized manual-review queue items with fields including `priority_score`, `sla_due_at`, and `is_overdue`.
- `GET /api/v1/applications/queue/metrics` (superuser): returns aggregate workload metrics.

Metric interpretation:

- `pending_manual_count`: number of applications currently waiting for reviewer action.
- `overdue_count`: number of pending-manual applications that passed `sla_due_at`.
- `high_priority_count`: number of pending-manual applications above the configured high-priority threshold.

## Reviewer Ops Playbook

Recommended daily triage sequence for review teams:

1. Open queue metrics and check `overdue_count` first.
2. Process overdue applications in descending `priority_score`.
3. Process remaining high-priority applications.
4. Use decision breakdown and document evidence before final action.
5. Submit review decision with a clear mandatory reason.
6. Audit trail automatically records action history for supervision and handoff.

## Why this approach

- **Fast to build and demo:** monolith architecture for MVP speed
- **Safer than black-box AI:** explainable scoring and explicit rules
- **Operationally credible:** supports human oversight and auditability
- **Extensible:** can incrementally add stronger OCR/ML models and policy rules

## Next planned phases

- Exportable decision/audit report for case handoff
- Stronger policy rule coverage aligned to legal requirements
- Production hardening (security, observability, governance)

## Technology Stack

- Backend: FastAPI, SQLModel, Pydantic, PostgreSQL
- Frontend: React, TypeScript, TanStack Router/Query, Tailwind CSS, shadcn/ui
- Infrastructure: Docker Compose, Traefik, JWT authentication
- Quality: Pytest backend tests and Playwright end-to-end tests

## Quick Start (Docker)

From the project root:

```bash
docker compose up -d --wait
```

Then open:

- Frontend: `http://localhost`
- API docs: `http://localhost/api/v1/docs`

## Local Development

- Backend setup and workflow: [backend/README.md](./backend/README.md)
- Frontend setup and workflow: [frontend/README.md](./frontend/README.md)
- Environment and stack details: [development.md](./development.md)

## Security Configuration

Before any shared or production deployment, rotate all default `changethis` credentials and secrets in `.env`.

At minimum, update:

- `SECRET_KEY`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_PASSWORD`

Deployment guidance: [deployment.md](./deployment.md)

## Further Reading

- [Release Notes](./release-notes.md)
- [Contributing](./CONTRIBUTING.md)
- [Security Policy](./SECURITY.md)

## License

This project is licensed under the terms of the MIT license.
