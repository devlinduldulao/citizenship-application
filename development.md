# Development Guide

This guide covers **full local development setup** for macOS, Ubuntu/Linux, and Windows — both using Docker (the recommended path) and running each service natively.

## Table of Contents

- [Quick Start with Docker (all platforms)](#quick-start-with-docker-all-platforms)
- [Platform Prerequisites](#platform-prerequisites)
  - [macOS](#macos)
  - [Ubuntu / Linux](#ubuntu--linux)
  - [Windows](#windows)
- [Environment File (.env) Reference](#environment-file-env-reference)
- [Native Local Development (without Docker)](#native-local-development-without-docker)
- [AI/ML Setup (Tesseract + spaCy)](#aiml-setup-tesseract--spacy)
- [Running Tests](#running-tests)
- [Linting and Formatting](#linting-and-formatting)
- [Docker Compose Details](#docker-compose-details)
- [Development URLs](#development-urls)

---

## Quick Start with Docker (all platforms)

Docker is the easiest and most consistent way to run the full stack on any OS.

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS, Windows) or Docker Engine + Compose plugin (Linux).

```bash
# Clone and enter the project
git clone <repo-url>
cd citizenship-application

# Start everything (PostgreSQL + backend + frontend + Adminer + Mailcatcher)
docker compose up -d --wait

# Or start with hot-reload (recommended for active development)
docker compose watch
```

Open your browser:

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Adminer (DB) | http://localhost:8080 |
| Mailcatcher | http://localhost:1080 |

Default login: `admin@example.com` / `changethis`

**The first run may take 1–2 minutes** while the backend waits for the database and applies migrations. Watch progress with:

```bash
docker compose logs -f backend
```

---

## Platform Prerequisites

### macOS

```bash
# 1. Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python 3.13+ and uv
brew install python@3.13
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install Bun (frontend runtime)
curl -fsSL https://bun.sh/install | bash

# 4. Install Docker Desktop
brew install --cask docker
# Then open Docker.app from Applications and complete the installation

# 5. Install Tesseract OCR (for scanned document and image processing)
brew install tesseract tesseract-lang
# No .env configuration needed — the backend auto-detects /opt/homebrew/bin/tesseract
# (Apple Silicon M1/M2/M3) or /usr/local/bin/tesseract (Intel)
```

### Ubuntu / Linux

```bash
# 1. Install Python 3.13+
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# 2. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install Bun
curl -fsSL https://bun.sh/install | bash

# 4. Install Docker
# Follow the official guide: https://docs.docker.com/engine/install/ubuntu/
# Quick method:
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # allow running docker without sudo (re-login required)
sudo apt install -y docker-compose-plugin

# 5. Install Tesseract OCR
sudo apt install -y tesseract-ocr tesseract-ocr-nor
# No .env configuration needed — auto-detected at /usr/bin/tesseract
```

### Windows

All commands below are run in PowerShell or Terminal.

```powershell
# 1. Install pyenv-win or Python 3.13+ directly from python.org
winget install Python.Python.3.13

# 2. Install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 3. Install Bun
powershell -c "irm bun.sh/install.ps1 | iex"

# 4. Install Docker Desktop
winget install Docker.DockerDesktop
# Open Docker Desktop and enable WSL2 integration in Settings

# 5. Install Tesseract OCR
winget install UB-Mannheim.TesseractOCR
# Default install path: C:\Program Files\Tesseract-OCR\tesseract.exe
# The backend auto-detects this location — no .env change needed.
# If you chose a custom install location, set it explicitly:
#   TESSERACT_CMD=C:\path\to\tesseract.exe
```

> **Windows note:** For the best experience, use [Windows Terminal](https://aka.ms/windows-terminal) and [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) for native Linux tooling. All shell scripts in the project assume a POSIX shell (bash/zsh); under WSL2 they run natively.

---

## Environment File (.env) Reference

The root `.env` file drives all services. Copy it from `.env.example` if starting fresh, or edit the existing one. Here is a full reference for every variable:

### General

| Variable | Default | Description |
|---|---|---|
| `DOMAIN` | `localhost` | Base domain. `localhost` for local dev; your real domain in staging/production. |
| `ENVIRONMENT` | `local` | One of `local`, `staging`, `production`. Controls security warnings and behavior. |
| `PROJECT_NAME` | `"Full Stack FastAPI Project"` | Displayed in API docs and emails. |
| `STACK_NAME` | `full-stack-fastapi-project` | Docker Compose project name (used for container naming). |
| `FRONTEND_HOST` | `http://localhost:5173` | The URL of the frontend. Used by the backend to build email links. In production, set to your domain e.g. `https://dashboard.example.com`. |

### Security

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `changethis` | **Must be changed before any real deployment.** Used to sign JWT tokens. Generate a strong key with: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `FIRST_SUPERUSER` | `admin@example.com` | Email address for the initial admin account created on first boot. |
| `FIRST_SUPERUSER_PASSWORD` | `changethis` | **Must be changed.** Password for the initial admin account. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `11520` (8 days) | JWT token lifetime in minutes. |

### CORS

| Variable | Default | Description |
|---|---|---|
| `BACKEND_CORS_ORIGINS` | `"http://localhost,http://localhost:5173,..."` | Comma-separated list of allowed frontend origins. In production, set to your frontend URL only e.g. `https://dashboard.example.com`. |

### Database (PostgreSQL)

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_SERVER` | `localhost` | Hostname of the PostgreSQL server. Use `localhost` for native dev; `db` when running through Docker Compose. |
| `POSTGRES_PORT` | `5432` | PostgreSQL port. |
| `POSTGRES_DB` | `app` | Database name. |
| `POSTGRES_USER` | `postgres` | Database user. |
| `POSTGRES_PASSWORD` | `changethis` | **Must be changed in any shared or production environment.** |

> **Tip (Docker):** When running `docker compose up`, the backend container connects to the `db` service by its Docker service name. The `.env` file sets `POSTGRES_SERVER=localhost` for native dev. When using Docker Compose the `compose.yml` overrides the server name to `db` automatically — you do not need to change `.env` when switching between native and Docker.

### Email (SMTP)

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | *(empty)* | SMTP server hostname. Leave empty to disable email sending. |
| `SMTP_USER` | *(empty)* | SMTP authentication username. |
| `SMTP_PASSWORD` | *(empty)* | SMTP authentication password. |
| `EMAILS_FROM_EMAIL` | `info@example.com` | The "From" address on outgoing emails. |
| `SMTP_TLS` | `True` | Enable STARTTLS. |
| `SMTP_SSL` | `False` | Enable SSL/TLS on connection (port 465). |
| `SMTP_PORT` | `587` | SMTP port. Common values: `587` (STARTTLS), `465` (SSL), `25` (plain). |

> **Local dev:** Docker Compose includes [Mailcatcher](http://localhost:1080) — a fake SMTP server that captures but does not send emails. No SMTP credentials are needed locally.

### AI / ML

| Variable | Default | Description |
|---|---|---|
| `TESSERACT_CMD` | *(empty)* | Path to the Tesseract binary. **Leave blank on macOS and Linux** — the backend auto-detects the Homebrew/apt install. On Windows, also auto-detected if installed via `winget` to the default location. Only set this if Tesseract is installed in a non-standard path. |
| `AI_EXPLAINER_BASE_URL` | *(empty)* | Base URL for an OpenAI-compatible LLM API. Leave blank to use the rules-based fallback case explainer. Example: `https://api.openai.com/v1` |
| `AI_EXPLAINER_API_KEY` | *(empty)* | API key for the LLM provider. |
| `AI_EXPLAINER_MODEL` | `gpt-4.1-mini` | Model name to use for case explanation. |
| `AI_EXPLAINER_TEMPERATURE` | `0.2` | LLM temperature (0–1). Lower = more deterministic. |
| `AI_EXPLAINER_TIMEOUT_SECONDS` | `20` | Request timeout for LLM calls. |

### Monitoring

| Variable | Default | Description |
|---|---|---|
| `SENTRY_DSN` | *(empty)* | Sentry DSN for error tracking. Leave empty to disable. |

### Docker Images

| Variable | Default | Description |
|---|---|---|
| `DOCKER_IMAGE_BACKEND` | `backend` | Docker image name for the backend. Override for a registry path e.g. `registry.example.com/myapp/backend`. |
| `DOCKER_IMAGE_FRONTEND` | `frontend` | Docker image name for the frontend. |

---

## Native Local Development (without Docker)

Use this path when you want faster iteration without container overhead. You still need Docker running for the database.

### 1. Start only the database

```bash
docker compose up -d db --wait
```

### 2. Backend

```bash
cd backend

# Install Python dependencies (first time or after pyproject.toml changes)
uv sync

# Apply database migrations
uv run alembic upgrade head

# Seed the initial superuser (first time only)
uv run python -m app.initial_data

# Start the dev server (auto-reloads on file save)
uv run fastapi dev app/main.py
# → http://localhost:8000  |  Swagger UI: http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend

# Install JS/TS dependencies (first time or after package.json changes)
bun install

# Start the dev server (hot module replacement)
bun run dev
# → http://localhost:5173
```

### 4. Stopping

```bash
# Stop just the database
docker compose stop db

# Or stop everything
docker compose down
```

---

## AI/ML Setup (Tesseract + spaCy)

Both are **optional**. The system degrades gracefully:
- Without Tesseract → digital PDFs still extract via PyMuPDF; scanned/image files return empty text
- Without spaCy → regex-only NLP handles entity extraction (dates, passport numbers, etc.)

### Tesseract OCR

| Platform | Command | Auto-detected? |
|---|---|---|
| macOS (Apple Silicon) | `brew install tesseract tesseract-lang` | ✅ Yes — `/opt/homebrew/bin/tesseract` |
| macOS (Intel) | `brew install tesseract tesseract-lang` | ✅ Yes — `/usr/local/bin/tesseract` |
| Ubuntu / Debian | `sudo apt install tesseract-ocr tesseract-ocr-nor` | ✅ Yes — `/usr/bin/tesseract` |
| Windows (default) | `winget install UB-Mannheim.TesseractOCR` | ✅ Yes — `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| Windows (custom path) | *(any installer)* | ❌ Set `TESSERACT_CMD=C:\custom\path\tesseract.exe` in `.env` |

Verify Tesseract is found by the backend:

```bash
cd backend
uv run python -c "from app.services.ocr import _configure_tesseract; _configure_tesseract(); import pytesseract; print(pytesseract.get_tesseract_version())"
```

### spaCy Norwegian Model

```bash
cd backend
uv pip install https://github.com/explosion/spacy-models/releases/download/nb_core_news_sm-3.8.0/nb_core_news_sm-3.8.0-py3-none-any.whl

# Verify
uv run python -c "import spacy; nlp = spacy.load('nb_core_news_sm'); print('spaCy OK')"
```

### LLM Case Explainer (optional)

Add to `.env` to enable GPT-backed case memos:

```dotenv
AI_EXPLAINER_BASE_URL=https://api.openai.com/v1
AI_EXPLAINER_API_KEY=sk-...
AI_EXPLAINER_MODEL=gpt-4.1-mini
```

Any OpenAI-compatible API works (Azure OpenAI, Ollama, etc.).

---

## Running Tests

### Backend

```bash
cd backend

# Unit + service tests only (no database required)
uv run pytest tests/unit tests/services -v

# Full suite (requires docker compose up -d db --wait first)
uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=term-missing
```

> The test suite automatically runs `alembic upgrade head` when the `db` fixture is first used — you do not need to run migrations manually before running tests.

### Frontend

```bash
cd frontend

# Run all unit tests
bun run test

# Watch mode (re-runs on file change)
bun run --bun vitest
```

### End-to-end OCR smoke test

Requires a running backend and database:

```bash
cd backend
uv run python scripts/smoke_ocr_nlp.py
```

---

## Linting and Formatting

### Backend (Ruff)

```bash
cd backend
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy app/             # type check
```

### Frontend (Biome)

```bash
cd frontend
bun run lint                 # lint + format (Biome)
```

### Pre-commit hooks (prek)

```bash
cd backend
uv run prek install -f       # install git pre-commit hook (run once)
```

From then on, Ruff and Biome run automatically on every `git commit`. To run all hooks manually:

```bash
uv run prek run --all-files
```

---

## Docker Compose Details

### Files

| File | Purpose |
|---|---|
| `compose.yml` | Base production-like stack definition |
| `compose.override.yml` | Dev overrides (source volume mounts, hot-reload) — applied automatically |
| `compose.traefik.yml` | Traefik reverse proxy (staging/production) |

### Useful commands

```bash
docker compose up -d --wait        # Start all services, wait until healthy
docker compose watch               # Start with live source sync (hot-reload)
docker compose logs -f backend     # Tail backend logs
docker compose logs -f             # Tail all logs
docker compose ps                  # Status of all services
docker compose stop frontend       # Stop one service (keep others running)
docker compose down                # Stop and remove containers
docker compose down -v             # Also remove volumes (wipes database!)
docker compose build --no-cache    # Rebuild images from scratch
```

### Swapping a service for a local process

Because each service binds to the same port whether run in Docker or locally, you can stop any container and start the local dev server in its place:

```bash
# Run frontend locally instead of in Docker
docker compose stop frontend
cd frontend && bun run dev         # same port :5173

# Run backend locally instead of in Docker
docker compose stop backend
cd backend && uv run fastapi dev app/main.py   # same port :8000
```

---

## Docker Compose in `localhost.tiangolo.com`

To test subdomain routing locally (mimicking production Traefik setup), change in `.env`:

```dotenv
DOMAIN=localhost.tiangolo.com
```

Then restart:

```bash
docker compose watch
```

| Service | URL |
|---|---|
| Frontend | http://dashboard.localhost.tiangolo.com |
| Backend | http://api.localhost.tiangolo.com |
| Swagger UI | http://api.localhost.tiangolo.com/docs |
| Adminer | http://localhost.tiangolo.com:8080 |
| Traefik UI | http://localhost.tiangolo.com:8090 |
| Mailcatcher | http://localhost.tiangolo.com:1080 |

`localhost.tiangolo.com` and all its subdomains resolve to `127.0.0.1` — no DNS change needed.

---

## Development URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Adminer (DB UI) | http://localhost:8080 |
| Traefik UI | http://localhost:8090 |
| Mailcatcher | http://localhost:1080 |
