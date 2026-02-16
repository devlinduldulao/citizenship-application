# Norwegian Citizenship Automation MVP — Agent Instructions

> IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any tasks in this project.
> Always explore the project structure before writing code. Read the nearest AGENTS.md in the directory you're editing.

## Project Overview

Full-stack monorepo automating Norway's citizenship application process. Combines document intake, OCR extraction, explainable rule-based eligibility scoring, caseworker decision support, and immutable audit trails. Targeted at UDI/Politi stakeholders.

**Domain model flow:** Intake → Document Upload → Background Processing → Eligibility Scoring → Human Review → Decision + Audit Trail

## Monorepo Layout

```
/                        ← Root: Docker Compose orchestration, shared config
├── backend/             ← FastAPI API server (Python, SQLModel, PostgreSQL)
│   ├── AGENTS.md        ← Backend-specific agent instructions
│   ├── app/             ← Application package (models, routes, core, CRUD)
│   ├── tests/           ← Pytest test suite
│   └── scripts/         ← Prestart, lint, test scripts
├── frontend/            ← React SPA (Vite, TanStack Router, Tailwind CSS)
│   ├── AGENTS.md        ← Frontend-specific agent instructions
│   ├── src/             ← Source (routes, components, hooks, client)
│   └── tests/           ← Playwright E2E tests
└── scripts/             ← Cross-project utility scripts
```

Each subproject has its own `AGENTS.md` with detailed conventions. **The nearest AGENTS.md to the file you're editing takes precedence.**

## Tech Stack Summary

| Layer      | Technology                                     | Package Manager |
| ---------- | ---------------------------------------------- | --------------- |
| Backend    | FastAPI 0.115, SQLModel, Pydantic 2, Alembic   | uv              |
| Frontend   | React 19, Vite 7, TanStack Router/Query, Zod 4 | bun             |
| Styling    | Tailwind CSS 4, shadcn/ui (Radix primitives)   | —               |
| Database   | PostgreSQL 18                                   | —               |
| Auth       | JWT (PyJWT + pwdlib[argon2,bcrypt])             | —               |
| Testing    | Pytest (backend), Playwright (frontend E2E)     | —               |
| Linting    | Ruff (backend), Biome (frontend)                | —               |
| Infra      | Docker Compose, Traefik reverse proxy           | —               |

## Setup Commands

### Full Stack (Docker — recommended)

```bash
docker compose up -d --wait          # Start all services
docker compose watch                 # Start with hot-reload (dev mode)
docker compose logs backend          # Tail backend logs
docker compose down                  # Stop everything
```

### Backend Only

```bash
cd backend
uv sync                              # Install dependencies
uv run fastapi dev app/main.py       # Dev server on :8000
uv run pytest                        # Run tests
uv run pytest --cov=app              # Tests with coverage
uv run ruff check .                  # Lint
uv run ruff format .                 # Format
uv run mypy app/                     # Type check
uv run alembic upgrade head          # Run migrations
uv run alembic revision --autogenerate -m "description"  # Generate migration
```

### Frontend Only

```bash
cd frontend
bun install                          # Install dependencies
bun run dev                          # Dev server on :5173
bun run build                        # Production build
bun run lint                         # Biome lint + format
bun run test                         # Playwright E2E tests
bun run generate-client              # Regenerate API client from OpenAPI
```

### From Root (workspace scripts)

```bash
bun run dev                          # Start frontend dev server
bun run lint                         # Lint frontend
bun run test                         # Run frontend tests
```

## Development URLs

| Service       | URL                            |
| ------------- | ------------------------------ |
| Frontend      | http://localhost:5173           |
| Backend API   | http://localhost:8000           |
| Swagger UI    | http://localhost:8000/docs      |
| ReDoc         | http://localhost:8000/redoc     |
| Adminer (DB)  | http://localhost:8080           |
| Mailcatcher   | http://localhost:1080           |

## Architecture & Key Patterns

### Backend (FastAPI + SQLModel)

- **Single models file:** All ORM models + Pydantic schemas live in `app/models.py` using SQLModel
- **CRUD layer:** `app/crud.py` contains all database operations
- **API routes:** `app/api/routes/` — one file per resource (`applications.py`, `users.py`, `items.py`, `login.py`)
- **Config:** `app/core/config.py` — Pydantic Settings reading from `../.env`
- **Auth:** JWT tokens via `app/core/security.py`, dependency injection in `app/api/deps.py`
- **Migrations:** Alembic in `app/alembic/versions/`

Key domain models: `CitizenshipApplication`, `ApplicationDocument`, `EligibilityRuleResult`, `ApplicationAuditEvent`

Application statuses: `draft → documents_uploaded → queued → processing → review_ready → approved | rejected | more_info_required`

### Frontend (React + Vite + TanStack Router)

- **File-based routing:** `src/routes/` — TanStack Router with auto-generated route tree
- **API client:** Auto-generated from backend OpenAPI spec (`src/client/`)
- **Components:** `src/components/` — shadcn/ui primitives in `ui/`, feature components in named folders
- **State:** TanStack Query for server state, local React state for UI
- **Theming:** `next-themes` provider with dark mode default

Route structure: `__root.tsx` → `_layout.tsx` → `{admin,applications,items,settings,index}.tsx` + auth routes (`login`, `signup`, `recover-password`, `reset-password`)

## Code Style & Naming

### Backend (Python)

- Files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Pydantic schemas: `PascalCase` with purpose suffix (`UserCreate`, `UserPublic`, `UserUpdate`)
- SQLModel tables: `PascalCase` singular (`User`, `CitizenshipApplication`)
- Linter: Ruff (strict mode, see `pyproject.toml` for rule set)
- Type checker: mypy (strict mode)

### Frontend (TypeScript)

- Files: `kebab-case.tsx`
- Variables/functions: `camelCase`
- Components/types: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Linter/formatter: Biome (configured in `biome.json`)
- No default exports (except TanStack Router route files)
- Imports use `@/` path alias for project root (`src/`)

## Testing Instructions

- **Backend:** `cd backend && uv run pytest` — all tests must pass before committing
- **Frontend E2E:** `cd frontend && bun run test` — Playwright tests against running stack
- **Coverage:** `uv run pytest --cov=app` for backend coverage report
- Add or update tests for every code change, even if not explicitly asked

## Pre-commit & Quality Gates

The project uses [prek](https://prek.j178.dev/) for pre-commit hooks. Install with:

```bash
cd backend && uv run prek install -f
```

Hooks run: Ruff lint + format (backend), Biome check (frontend), TOML/YAML validation, large file checks.

## Security Considerations

- **Never commit `.env` with real secrets.** Rotate all `changethis` defaults before any shared deployment.
- Critical secrets: `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, `POSTGRES_PASSWORD`
- Auth: JWT tokens stored in `localStorage`, auto-redirect on 401/403
- CORS: configured via `BACKEND_CORS_ORIGINS` env var
- Passwords: hashed with Argon2/bcrypt via `pwdlib`

## PR / Commit Guidelines

- Run `uv run ruff check . && uv run pytest` (backend) and `bun run lint && bun run test` (frontend) before committing
- Add/update tests for any code changes
- Use descriptive commit messages
- Title format: `[component/feature] Description`
- Include Alembic migrations for any model changes
- Keep PRs focused on a single change

## Environment Variables

All configuration is in the root `.env` file. Key variables:

| Variable                    | Purpose                          |
| --------------------------- | -------------------------------- |
| `SECRET_KEY`                | JWT signing key                  |
| `POSTGRES_SERVER/PORT/USER/PASSWORD/DB` | Database connection    |
| `FIRST_SUPERUSER`           | Initial admin email              |
| `FIRST_SUPERUSER_PASSWORD`  | Initial admin password           |
| `FRONTEND_HOST`             | CORS allowed frontend origin     |
| `BACKEND_CORS_ORIGINS`      | Additional CORS origins          |
| `ENVIRONMENT`               | `local`, `staging`, `production` |
| `SMTP_HOST/USER/PASSWORD`   | Email sending (Mailcatcher local)|

## Detailed Documentation

| Topic           | Location                                              |
| --------------- | ----------------------------------------------------- |
| Backend details | `backend/AGENTS.md`, `backend/README.md`              |
| Frontend details| `frontend/AGENTS.md`, `frontend/README.md`            |
| Development     | `development.md`                                      |
| Deployment      | `deployment.md`                                       |
| Contributing    | `CONTRIBUTING.md`                                     |
| Release Notes   | `release-notes.md`                                    |
| Security        | `SECURITY.md`                                         |
