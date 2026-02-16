# Norwegian Citizenship Automation MVP - Backend

This backend provides the API and decisioning engine for the citizenship manual-review triage system. It sits on top of UDI/Politi's existing automated pipeline, targeting specifically the flagged and complex cases that land in the manual review queue.

## Backend responsibilities

- Applicant case intake and application lifecycle management
- Requirement document upload and processing pipeline orchestration
- Real OCR text extraction (PyMuPDF) and NLP entity recognition (regex-based)
- Explainable eligibility scoring with NLP-enhanced weighted rules
- Caseworker review decisions (`approve`, `reject`, `request_more_info`)
- Immutable audit trail for system and human actions

## AI / ML Pipeline

The backend contains a three-stage document intelligence pipeline:

1. **OCR extraction** (`app/services/ocr.py`) — PyMuPDF extracts text from digital PDFs; Pillow + pytesseract handles scanned documents and images
2. **NLP entity extraction** (`app/services/nlp.py`) — regex patterns tuned for Norwegian citizenship documents extract dates, passport numbers, nationalities, names, language/residency indicators, and citizenship keywords
3. **Rule engine** (`app/api/routes/applications.py`) — 7 weighted rules combine document-type signals with NLP-extracted evidence for explainable scoring

## Implemented API domains

- Auth and user management (`/login`, `/users`)
- Applications and documents (`/applications`)
- Automated pre-screening + decision breakdown (`/applications/{id}/decision-breakdown`)
- Caseworker actions + audit (`/applications/{id}/review-decision`, `/applications/{id}/audit-trail`)
- Reviewer workload queue + SLA metrics (`/applications/queue/review`, `/applications/queue/metrics`)

## Queue & SLA operations

These endpoints are superuser-only and are used to monitor and prioritize manual review workload.

- `GET /api/v1/applications/queue/review`
	- Returns pending manual-review applications sorted by priority.
	- Includes queue-facing fields such as `priority_score`, `sla_due_at`, and `is_overdue`.
- `GET /api/v1/applications/queue/metrics`
	- Returns aggregate operational counts for reviewer throughput.

Metric definitions:

- `pending_manual_count`: applications currently awaiting manual review.
- `overdue_count`: pending-manual applications where current time is past `sla_due_at`.
- `high_priority_count`: pending-manual applications above the high-priority threshold.

### Reviewer Ops Playbook

Suggested operational flow for API consumers and reviewer teams:

1. Call `GET /api/v1/applications/queue/metrics` and inspect `overdue_count`.
2. Call `GET /api/v1/applications/queue/review` and process overdue items first.
3. Continue with highest `priority_score` items in pending manual queue.
4. Use decision-breakdown and uploaded document context before deciding.
5. Submit final review action with mandatory reason; rely on audit trail for traceability.

The core data and schema definitions are in `./backend/app/models.py` and route handlers are in `./backend/app/api/routes/`.

## Requirements

* [Docker](https://www.docker.com/).
* [uv](https://docs.astral.sh/uv/) for Python package and environment management.

## Docker Compose

Start the local development environment with Docker Compose following the guide in [../development.md](../development.md).

## General Workflow

By default, the dependencies are managed with [uv](https://docs.astral.sh/uv/), go there and install it.

From `./backend/` you can install all the dependencies with:

```console
$ uv sync
```

Then you can activate the virtual environment with:

```console
$ source .venv/bin/activate
```

Make sure your editor is using the correct Python virtual environment, with the interpreter at `backend/.venv/bin/python`.

Modify or add SQLModel models for data and SQL tables in `./backend/app/models.py`, API endpoints in `./backend/app/api/`, and reusable domain logic in dedicated modules under `./backend/app/`.

## VS Code

There are already configurations in place to run the backend through the VS Code debugger, so that you can use breakpoints, pause and explore variables, etc.

The setup is also already configured so you can run the tests through the VS Code Python tests tab.

## Docker Compose Override

Development-only overrides go in `compose.override.yml`. Key behaviours:

- Backend source directory is volume-mounted for live code sync.
- `fastapi run --reload` restarts on file changes (single worker).
- Use `docker compose exec backend bash` to open a shell inside the container.

## Backend tests

To test the backend run:

```console
$ bash ./scripts/test.sh
```

The tests run with Pytest, modify and add tests to `./backend/tests/`.

For the citizenship MVP APIs, focused route tests are in:

- `./backend/tests/api/routes/test_applications.py`

If you use GitHub Actions the tests will run automatically.

### Test running stack

If your stack is already up and you just want to run the tests, you can use:

```bash
docker compose exec backend bash scripts/tests-start.sh
```

That `/app/scripts/tests-start.sh` script just calls `pytest` after making sure that the rest of the stack is running. If you need to pass extra arguments to `pytest`, you can pass them to that command and they will be forwarded.

For example, to stop on first error:

```bash
docker compose exec backend bash scripts/tests-start.sh -x
```

### Test Coverage

When the tests are run, a file `htmlcov/index.html` is generated, you can open it in your browser to see the coverage of the tests.

## Migrations

As during local development your app directory is mounted as a volume inside the container, you can also run the migrations with `alembic` commands inside the container and the migration code will be in your app directory (instead of being only inside the container). So you can add it to your git repository.

Make sure you create a "revision" of your models and that you "upgrade" your database with that revision every time you change them. As this is what will update the tables in your database. Otherwise, your application will have errors.

* Start an interactive session in the backend container:

```console
$ docker compose exec backend bash
```

* Alembic is already configured to import your SQLModel models from `./backend/app/models.py`.

* After changing a model (for example, adding a column), inside the container, create a revision, e.g.:

```console
$ alembic revision --autogenerate -m "Add column last_name to User model"
```

* Commit to the git repository the files generated in the alembic directory.

* After creating the revision, run the migration in the database (this is what will actually change the database):

```console
$ alembic upgrade head
```

If you don't want to use migrations at all, uncomment the lines in the file at `./backend/app/core/db.py` that end in:

```python
SQLModel.metadata.create_all(engine)
```

and comment the line in the file `scripts/prestart.sh` that contains:

```console
$ alembic upgrade head
```

If you don't want to start with the default models and want to remove them / modify them, from the beginning, without having any previous revision, you can remove the revision files (`.py` Python files) under `./backend/app/alembic/versions/`. And then create a first migration as described above.

Recent MVP migrations include citizenship domain tables for:

- applications and uploaded documents,
- eligibility rule results,
- review decisions and audit events.

## Code Structure

Key backend paths:

- `app/models.py` — SQLModel domain models (applications, documents, rules, audit events)
- `app/services/ocr.py` — OCR text extraction (PyMuPDF + Tesseract fallback)
- `app/services/nlp.py` — Regex NLP entity extraction (dates, passport numbers, nationalities, etc.)
- `app/api/routes/applications.py` — citizenship workflow endpoints with NLP-enhanced rule engine
- `app/api/deps.py` — dependency injection (DB sessions, auth)
- `app/core/config.py` — settings and environment
- `app/alembic/versions/` — migration history
- `tests/api/routes/test_applications.py` — route-level test coverage
- `tests/services/test_ocr_nlp.py` — OCR and NLP unit tests (17 tests)
- `scripts/smoke_ocr_nlp.py` — live end-to-end OCR/NLP smoke test

## Email Templates

Email templates live in `./backend/app/email-templates/`. Edit `.mjml` sources in `src/`, then export to HTML in `build/` using the VS Code MJML extension (`Ctrl+Shift+P` → `MJML: Export to HTML`).
