# Norwegian Citizenship Automation MVP

## What this project is about

This project is a **monolithic MVP** that accelerates the manual review queue in Norway's citizenship application pipeline.

### The problem

UDI and Politi already have automated systems that handle straightforward citizenship applications — cases with complete documentation and no flags pass through without manual intervention. The bottleneck is the **manual triage queue**: applications that are flagged, incomplete, or require human judgment. This queue grows faster than reviewers can process it (limited staffing, rising application volumes), resulting in wait times that can exceed **2 years**.

### What this system does

This MVP sits **on top of** UDI/Politi's existing automated pipeline. It targets specifically the cases that land in the manual review pile:

- **Structured intake and document upload** — standardizes how flagged cases enter the review queue.
- **OCR/NLP-assisted extraction** — pre-parses uploaded documents so reviewers don't start from scratch.
- **Explainable rule-based pre-screening** — scores each case with transparent, weighted rules. Reviewers see exactly why a case scored the way it did.
- **Priority and SLA management** — ranks the backlog by urgency and risk so the most critical cases are reviewed first.
- **Decision support, not decision replacement** — the system recommends; a human reviewer always makes the final call.
- **Immutable audit trail** — every action (system and human) is logged for supervision, accountability, and legal compliance.

### Who it's for

The intended audience is **UDI/Politi operations teams** — specifically the reviewers, team leads, and managers who handle the manual backlog. The goal is not to replace their existing automation, but to give them tools to clear the growing pile of flagged cases faster and more consistently.

## Maintainer

- **Devlin Duldulao** — Senior Software Engineer, Crayon Consulting AS (Oslo, Norway)

## Documentation Map

- [Root README](./README.md): architecture overview, setup, and runtime workflow
- [Backend README](./backend/README.md): API domains, backend workflow, AI/OCR/NLP services
- [Frontend README](./frontend/README.md): UI workflow, generated client usage, API call guard
- [Development Guide](./development.md): environment and local development details
- [Deployment Guide](./deployment.md): deployment and operations guidance
- [Roadmap](./ROADMAP.md): phased delivery plan for product + AI evolution
- [Immigrant User Guide](./IMMIGRANT_USER_GUIDE.md): step-by-step applicant journey
- [Reviewer Admin Guide](./REVIEWER_ADMIN_GUIDE.md): step-by-step UDI/Politi/admin workflow
- [Contributing Guide](./CONTRIBUTING.md): contributor workflow and review expectations
- [Code of Conduct](./CODE_OF_CONDUCT.md): community standards and behavior expectations
- [Support](./SUPPORT.md): where to ask questions and report non-security issues
- [Security Policy](./SECURITY.md): vulnerability reporting and disclosure flow
- [Governance](./GOVERNANCE.md): maintainer roles and decision process
- [Changelog](./CHANGELOG.md): release tracking entry point
- [Authors](./AUTHORS.md): maintainers and contributors

## MVP scope (implemented)

### Phase 1 — Intake and processing pipeline

- Citizenship application creation and management
- Requirement document upload (PDF/image)
- Background processing pipeline with real OCR and NLP extraction

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
- `GET /api/v1/applications/{application_id}/case-explainer`: returns AI-assisted case memo (`summary`, `recommended_action`, `key_risks`, `missing_evidence`, `next_steps`) with optional LLM generation and rules-based fallback.
- `GET /api/v1/applications/{application_id}/evidence-recommendations`: returns AI-guided missing-document recommendations and next actions.

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

## AI / ML Architecture

The system uses a three-stage intelligent pipeline for document analysis:

### Stage 1 — Document Intelligence (OCR)

| Technology | Purpose | When used |
|---|---|---|
| **PyMuPDF (fitz)** | Text-layer extraction from digital PDFs | Primary — handles most uploads |
| **Pillow + pytesseract** | Image preprocessing and optical character recognition | Fallback — for scanned documents and image uploads |

Extraction returns structured metadata: method used, confidence score, character count, page count, and any warnings (e.g. `ocr_unavailable` if Tesseract is not installed).

### Stage 2 — Entity Extraction (NLP)

Hybrid NLP pipeline combining a trained Norwegian spaCy model and domain-tuned regex patterns. Extracts:

| Entity type | Examples |
|---|---|
| **Dates** | `15.03.1990`, `2023-01-15`, `15 mars 1990`, `20 oktober 2024` |
| **Passport numbers** | `NO1234567`, fødselsnummer patterns (`ddmmyyXXXXX`) |
| **Nationalities** | 50+ nationalities in English and Norwegian |
| **Names** | Surname/given name fields, title-case sequences, spaCy `PER` entities |
| **Locations/addresses** | spaCy `GPE/LOC` entities + Norwegian postal/street patterns |
| **Citizenship keywords** | `statsborgerskap`, `permanent residence`, `oppholdstillatelse` |
| **Language indicators** | `norskprøve`, `B1`, `B2`, `bestått`, `kompetanse norge` |
| **Residency indicators** | `bodd i Norge`, `folkeregisteret`, `years in Norway` |
| **Addresses** | Norwegian postal code patterns, street addresses |

Each document receives an NLP score (0–1) based on entity richness across categories.

### Stage 3 — Explainable Rule Engine

7 weighted rules combine document-type signals with NLP-extracted evidence:

| Rule | Weight | NLP enhancement |
|---|---|---|
| Identity document present | 0.20 | Passport number in text boosts score even without matching doc type |
| Residency evidence present | 0.18 | NLP residency keywords can partially satisfy the rule |
| Document OCR/NLP quality | 0.17 | Includes avg NLP entity richness score |
| Language/integration evidence | 0.15 | Language proficiency indicators found in text |
| Security screening evidence | 0.15 | Police clearance document detection |
| NLP entity richness | 0.10 | Total entities extracted across all documents |
| Residency duration signal | 0.05 | Case notes + NLP residency signals combined |

Every rule includes a human-readable rationale and full evidence payload so reviewers can verify the system's reasoning.

## Where AI is applied now

- **Document understanding:** OCR + NLP extraction for uploaded evidence.
- **Case narrative generation:** `case-explainer` endpoint produces a reviewer-ready case memo with fallback behavior if LLM is unavailable.
- **Evidence gap recommendations:** `evidence-recommendations` endpoint suggests high-impact missing document types and next actions.
- **Human-in-the-loop controls:** AI outputs are advisory; final decisions remain caseworker-owned and auditable.

## AI Hackathon talking points

- **Real AI in production flow:** Tesseract OCR + spaCy Norwegian NER are live in the processing pipeline.
- **Explainable AI, not black box:** Every recommendation is linked to rule evidence, extracted entities, and traceable rationale.
- **Human-in-the-loop governance:** AI assists triage and explanation; caseworkers keep final decision authority.
- **Demo-ready value:** Uploading real documents triggers OCR, entity extraction, confidence scoring, and reviewer guidance end-to-end.

## Hackathon pitch scripts

### On-stage cheat sheet (60–90 seconds)

**Hook (10s):** "We built an AI-assisted citizenship review system that reduces manual triage time while keeping humans in control."

**What it does (20s):** "The pipeline reads uploaded files with OCR (PyMuPDF + Tesseract), extracts key evidence with NLP (spaCy Norwegian NER + domain rules), and produces an explainable confidence/risk breakdown."

**Why it matters (15s):** "Reviewers don’t just get a score—they get rule-by-rule rationale and evidence. That improves speed, consistency, and trust."

**Governance (10s):** "This is human-in-the-loop by design: AI assists, caseworkers decide, and actions are auditable."

**Roadmap close (10s):** "Next, we add citation-grounded copilot Q&A, queue risk prediction, and anomaly detection."

**Transition line:** "Now I’ll show one live case going from upload to explainable recommendation."

### 1-minute pitch

"We built an AI-assisted citizenship review system for Norway focused on the real bottleneck: manual document triage.

When someone uploads documents, we run OCR with PyMuPDF and Tesseract to read both digital and scanned files. Then we run NLP with spaCy Norwegian NER plus domain-specific extraction to detect identities, dates, nationalities, residency, and language signals. Finally, an explainable rule engine turns that evidence into confidence, risk level, and a reviewer recommendation.

This isn’t black-box automation. Every score is traceable to evidence, and final decisions always stay with human caseworkers. So we improve speed and consistency while keeping trust and accountability." 

### 3-minute pitch

"Today, citizenship caseworkers spend too much time on repetitive document checks. Our system gives them an AI copilot for evidence review while keeping people in control.

Step 1 is document intelligence. We extract text from uploads using PyMuPDF for digital PDFs and Tesseract OCR for scans and images. Step 2 is NLP understanding. We combine spaCy’s Norwegian model with domain rules to identify key entities like names, passport numbers, dates, nationalities, language indicators, and residency clues. Step 3 is explainable scoring. Seven weighted rules turn that evidence into a confidence score, risk level, and rule-by-rule rationale.

For reviewers, this means they don’t just see a score—they see why. Which rules passed, what evidence was found, and what is still missing. We also generate case explanations and evidence recommendations to reduce cognitive load.

Most importantly, this is human-in-the-loop by design. AI helps with triage and consistency, but final approvals and rejections remain caseworker decisions, captured in an immutable audit trail.

From here, our roadmap adds retrieval-grounded reviewer Q&A, queue risk prediction, anomaly detection across documents, and active-learning feedback from reviewer corrections. So this MVP is already useful today and built to scale into a stronger public-sector AI platform." 

### Suggested live demo flow (2–4 minutes)

1. Create/open an application and upload `passport` + `language_certificate` sample files.
2. Trigger processing and show extracted OCR text and entities.
3. Open decision breakdown and highlight rule evidence + rationale.
4. Show missing-evidence recommendation and explain human final decision control.
5. Close with roadmap: copilot Q&A, risk forecasting, anomaly detection.

### Speaking style variants (pick one)

**Recommended default for hackathon judges:** Start with **Energetic** for the first 20–30 seconds to hook attention, then shift to **Formal** for architecture, governance, and Q&A credibility.

**Transition cue (say this verbatim):** "Now I’ll quickly switch from the problem framing to how the system works, why it’s explainable, and how governance is built in."

**Closing transition cue (say this verbatim):** "You’ve seen the system work end-to-end, so I’ll close with what we can deliver next: reviewer copilot Q&A, risk prediction, and stronger governance at production scale."

**Final 10-second close (say this verbatim):** "Thank you for your time—our goal is simple: faster citizenship review with explainable AI and human accountability. We’d love your feedback on where this should be piloted first."

#### Energetic

"We’re solving a real public-sector bottleneck: manual citizenship document triage. Our AI pipeline reads uploaded files with OCR, understands key evidence with NLP, and produces explainable recommendations reviewers can trust. The key point is this: we speed up decisions without losing human control. Every score is evidence-backed, auditable, and ready for real operations—not just a hackathon demo."

#### Formal

"This solution addresses a high-friction stage in citizenship processing: evidence triage during manual review. The system applies OCR and NLP to transform unstructured documents into structured, explainable signals. These signals are evaluated through transparent weighted rules that produce confidence and risk outputs with explicit rationale. Final authority remains with caseworkers, ensuring governance, accountability, and operational trust."

#### Simple English

"Our system helps officers review citizenship documents faster. First, it reads documents with OCR. Second, it finds important information with NLP, like names, dates, and passport numbers. Third, it gives a clear score with reasons. People still make the final decision. So the system saves time, keeps quality high, and stays safe and transparent."

## 6-slide pitch outline (presenter notes)

### Slide 1 — Problem

- Citizenship case review is document-heavy, repetitive, and time-constrained.
- Manual triage creates queue bottlenecks and inconsistent outcomes.
- Caseworkers need faster evidence synthesis without losing governance.

**Talk track:** "The bottleneck isn’t data entry—it’s review time per case. We cut review friction while keeping accountability intact."

### Slide 2 — Solution

- AI-assisted review workflow for uploaded citizenship documents.
- Converts unstructured files into structured evidence and reviewer guidance.
- Keeps final approval/rejection decisions with human caseworkers.

**Talk track:** "We support decisions; we don’t replace decision-makers."

### Slide 3 — AI architecture

- OCR layer: PyMuPDF + Tesseract for digital and scanned documents.
- NLP layer: spaCy Norwegian NER + domain regex extraction.
- Explainability layer: weighted rules with evidence and rationale per rule.

**Talk track:** "Every score is inspectable: what we extracted, which rule triggered, and why."

### Slide 4 — Live demo

- Upload `passport` and `language_certificate` sample documents.
- Trigger processing and show OCR text + extracted entities.
- Open decision breakdown and highlight confidence, risk, and failed rules.

**Talk track:** "In under a minute, reviewers move from raw files to a structured case view."

### Slide 5 — Impact

- Faster triage for manual-review queues.
- More consistent reviewer decisions through standardized evidence views.
- Stronger trust via human-in-the-loop controls and audit trail.

**Talk track:** "Speed, consistency, and governance improve together—not as trade-offs."

### Slide 6 — Roadmap

- Retrieval-grounded reviewer copilot Q&A with citations.
- Queue risk prediction and proactive SLA breach alerts.
- Cross-document anomaly detection and active-learning feedback loops.

**Talk track:** "This MVP is useful now and ready to grow into a full public-sector AI copilot."

## Judge Q&A cheat sheet

### Is this real AI or just rules?

It’s both. We use real AI components in the production flow:

- OCR with Tesseract for scanned/image documents.
- NLP with spaCy Norwegian NER for entity recognition.
- Rule-based explainability layer to convert evidence into transparent scoring.

This hybrid design is easier to trust and audit than black-box-only models.

### Why not use an LLM for everything?

- Public-sector decisions require traceability and reproducibility.
- Deterministic rules are easier to audit and govern.
- We use generative components for assistance (case explanation/recommendations), not final decisions.

### How do you avoid bias and unfair automation?

- Human-in-the-loop by default: final decision stays with the caseworker.
- Rule-level rationale and evidence are shown for every recommendation.
- Audit trail records all processing and review actions.
- Roadmap includes monitoring and governance controls for model behavior.

### What happens if OCR or NLP fails?

- Graceful degradation is built in.
- Without Tesseract, digital PDFs still process via PyMuPDF.
- Without spaCy model, regex extraction still runs.
- Failures reduce confidence and increase review priority rather than auto-rejecting.

### How accurate is it?

Accuracy depends on the scenario and document quality.

- We show confidence and per-rule evidence instead of claiming perfect automation.
- The system is designed to improve triage quality and consistency, not replace legal review.
- Active-learning feedback from reviewers is in the roadmap.

### What is the measurable value for operations?

- Faster triage by pre-structuring evidence from raw documents.
- More consistent manual decisions using shared explainable criteria.
- Better queue control via confidence/risk-aware prioritization.

### Is the data secure?

- Standard API auth (JWT) and backend access controls are in place.
- Decisions and reviewer actions are logged in an audit trail.
- Production hardening (expanded governance/monitoring) is explicitly in roadmap scope.

### What makes this hackathon project credible beyond demo day?

- Real end-to-end processing (upload → OCR → NLP → explainable scoring → review guidance).
- Automated tests for backend/frontend and OCR/NLP service behavior.
- Clear phased roadmap from MVP to governance-grade production capability.

## Closing + demo fallback lines

### 30-second closing statement

"This project shows practical public-sector AI: real OCR and NLP in the workflow, explainable recommendations instead of black-box outcomes, and clear human accountability for final decisions. We reduce reviewer workload and improve consistency today, and our roadmap adds citation-grounded copilot support, risk forecasting, and stronger governance. In short: useful now, trustworthy by design, and built to scale responsibly." 

### Fallback answer 1 — If live processing is slow

"The pipeline is asynchronous by design, so brief delays don’t block reviewers. While this request completes, I can show the same end-to-end result from our smoke test output: extracted entities, rule breakdown, confidence score, and recommendation rationale." 

### Fallback answer 2 — If OCR/NLP service dependency is unavailable

"The system is built with graceful degradation. If Tesseract or spaCy is unavailable, we still process what we can, lower confidence accordingly, and prioritize human review instead of making unsafe automated conclusions." 

### Fallback answer 3 — If frontend demo fails

"The backend contract and logic are independently verifiable. We can demonstrate the same workflow through API endpoints and test outputs: upload, extraction, rule scoring, and audit evidence are all reproducible without UI dependence." 

## AI expansion opportunities

- Reviewer copilot Q&A grounded in rules, extracted evidence, and audit trail citations.
- Backlog risk forecasting (`likely_more_info_required`, SLA breach prediction) for queue prioritization.
- Cross-document anomaly detection for identity/residency inconsistencies and missing evidence patterns.
- Multilingual summarization and translation assistance for reviewer notes and applicant-facing communication.

## Testing with sample documents

The system performs **real OCR text extraction and NLP entity recognition** on uploaded files. Upload actual PDFs with text content to get meaningful extraction results.

Upload files with these `document_type` values to trigger different eligibility rules:

| `document_type` value | Rule it satisfies |
|---|---|
| `passport` or `id_card` | Identity document present |
| `residence_permit`, `residence_proof`, or `tax_statement` | Residency evidence present |
| `language_certificate`, `norwegian_test`, or `education_certificate` | Language/integration evidence |
| `police_clearance` | Security screening evidence |

For the **highest confidence score**, upload one document per category (e.g. a passport PDF, a residence_permit PDF, a language_certificate image, and a police_clearance PDF). Add case notes mentioning "long-term residence" or "years" to trigger the bonus residency-duration rule.

For a **low confidence / high risk** case, upload only a single passport — the missing categories will pull the score down and flag the case for priority manual review.

### Live smoke test

An end-to-end smoke test creates realistic passport and language certificate PDFs (using PyMuPDF), uploads them, triggers processing, and verifies extraction results:

```bash
cd backend
uv run python scripts/smoke_ocr_nlp.py
```

Expected output includes extracted passport numbers, nationalities, language indicators, dates, and NLP-enhanced rule scoring.

## Why this approach

- **Targets the real bottleneck:** works on the manual review pile, not the already-automated happy path
- **Fast to build and demo:** monolith architecture for MVP speed
- **Safer than black-box AI:** explainable scoring and explicit rules
- **Operationally credible:** supports human oversight and auditability
- **Real AI pipeline:** PyMuPDF document intelligence, regex NLP entity extraction, and NLP-enhanced scoring
- **Extensible:** can incrementally add stronger OCR/ML models (spaCy, transformer NER) and policy rules

## Next planned phases

- Exportable decision/audit report for case handoff
- Stronger policy rule coverage aligned to legal requirements
- Production hardening (security, observability, governance)

## Technology Stack

- Backend: FastAPI, SQLModel, Pydantic, PostgreSQL
- AI/ML: PyMuPDF (document intelligence), Pillow (image processing), pytesseract + Tesseract OCR (scanned documents), spaCy `nb_core_news_sm` (Norwegian NER), regex NLP (domain-specific entity extraction)
- Frontend: React, TypeScript, TanStack Router/Query, Tailwind CSS, shadcn/ui
- Infrastructure: Docker Compose, Traefik, JWT authentication
- Quality: Pytest backend tests (including OCR/NLP unit tests) and Vitest frontend unit tests

## Quick Start (Docker)

From the project root:

```bash
docker compose up -d --wait
```

Then open:

- Frontend: `http://localhost`
- API docs: `http://localhost/api/v1/docs`

## Local Development

### Prerequisites

- [Python 3.13+](https://www.python.org/) with [uv](https://docs.astral.sh/uv/) package manager (3.13 required for spaCy compatibility)
- [Bun](https://bun.sh/) (frontend package manager and runtime)
- [Docker](https://www.docker.com/) (for PostgreSQL)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (for scanned document / image OCR)

### 1. Start the database

```bash
docker compose up -d db --wait
```

### 2. Start the backend

```bash
cd backend
uv sync                             # install dependencies (first time)
uv run alembic upgrade head         # run database migrations
uv run python -m app.initial_data   # seed superuser (first time)
uv run fastapi dev app/main.py      # dev server → http://localhost:8000
```

### 2b. Install AI/ML dependencies (first time)

```bash
# Install Tesseract OCR (Windows — choose one):
winget install UB-Mannheim.TesseractOCR
# or: choco install tesseract -y  (requires admin)
# Linux: sudo apt install tesseract-ocr tesseract-ocr-nor
# macOS: brew install tesseract tesseract-lang

# Set Tesseract path in .env (Windows example — adjust to your install location):
# TESSERACT_CMD=C:\Users\<you>\AppData\Local\Programs\Tesseract-OCR\tesseract.exe

# Install spaCy Norwegian language model:
uv pip install https://github.com/explosion/spacy-models/releases/download/nb_core_news_sm-3.8.0/nb_core_news_sm-3.8.0-py3-none-any.whl

# Verify both work:
uv run python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
uv run python -c "import spacy; nlp = spacy.load('nb_core_news_sm'); print('spaCy OK')"

# Verify using app config path (recommended on Windows when Tesseract is not on PATH):
uv run python -c "from app.core.config import settings; import pytesseract; pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD or pytesseract.pytesseract.tesseract_cmd; print(pytesseract.get_tesseract_version())"

# Optional: enable LLM-backed case explainer (OpenAI-compatible API)
# AI_EXPLAINER_BASE_URL=https://api.openai.com/v1
# AI_EXPLAINER_API_KEY=your_api_key
# AI_EXPLAINER_MODEL=gpt-4.1-mini
```

> **Note:** Both Tesseract and spaCy are optional. The system degrades gracefully:
> - Without Tesseract: digital PDFs still work via PyMuPDF, but scanned/image docs return empty text
> - Without spaCy: regex-based NLP handles all entity extraction (dates, passport numbers, keywords, etc.)

API docs available at http://localhost:8000/docs (Swagger UI) and http://localhost:8000/redoc.

### 3. Start the frontend

```bash
cd frontend
bun install                         # install dependencies (first time)
bun run dev                         # dev server → http://localhost:5173
```

### 4. Run tests

```bash
# Backend unit tests (no DB required)
cd backend && uv run pytest tests/unit -v

# Backend full test suite (requires running DB)
cd backend && uv run pytest

# Frontend unit tests
cd frontend && bun run test
```

### 5. Build for production

```bash
# Frontend production build
cd frontend && bun run build        # outputs to frontend/dist/

# Backend Docker image (must run from project root)
docker build -t citizenship-backend -f backend/Dockerfile .
```

### 6. Lint and format

```bash
# Backend
cd backend && uv run ruff check .   # lint
cd backend && uv run ruff format .  # format

# Frontend
cd frontend && bun run lint         # Biome lint + format

# Monorepo contract guard (generated frontend client usage)
bun run verify:api-contract
```

### Development URLs

| Service       | URL                       |
|---------------|---------------------------|
| Frontend      | http://localhost:5173      |
| Backend API   | http://localhost:8000      |
| Swagger UI    | http://localhost:8000/docs |
| ReDoc         | http://localhost:8000/redoc|
| Adminer (DB)  | http://localhost:8080      |
| Mailcatcher   | http://localhost:1080      |

### Default credentials

| User             | Email               | Password     |
|------------------|---------------------|--------------|
| Superuser/Admin  | admin@example.com   | changethis   |

For demo UX, the login page at `http://localhost:5173/login` is prefilled with these credentials by default.

> **Warning:** Rotate all `changethis` defaults in `.env` before any shared deployment.

### Login troubleshooting (spinner / CORS / devtools noise)

If login keeps spinning, run these checks in order:

```bash
# 1) Ensure DB is healthy and reachable
docker compose up -d db --wait

# 2) Ensure admin user exists
cd backend
uv run python -m app.initial_data

# 3) Start backend from project root with explicit project path
cd ..
uv run --project backend fastapi dev backend/app/main.py --port 8000

# 4) Start frontend (configured to use strict port 5173)
cd frontend
bun run dev
```

Then hard-refresh the browser (`Ctrl+Shift+R`) and retry login.

If Chrome console shows `chrome-extension://...` errors (message port / frame errors),
those are from browser extensions (often password managers), not from this app. Test
in Incognito mode (with extensions disabled) to verify app behavior.

### More details

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
- [Roadmap](./ROADMAP.md)
- [Code of Conduct](./CODE_OF_CONDUCT.md)
- [Support](./SUPPORT.md)
- [Governance](./GOVERNANCE.md)
- [Changelog](./CHANGELOG.md)

## License

This project is licensed under the terms of the MIT license.
