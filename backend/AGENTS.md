# Norwegian Citizenship Automation — Backend Agent Instructions

> IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any tasks in this project.
> Always explore the project structure before writing code.

## Tech Stack

| Category         | Technology                  | Version / Constraint      |
| ---------------- | --------------------------- | ------------------------- |
| Language         | Python                      | >=3.10, <4.0              |
| Framework        | FastAPI                     | >=0.114.2, <1.0.0         |
| ORM / Schemas    | SQLModel (wraps SQLAlchemy) | >=0.0.21, <1.0.0          |
| Validation       | Pydantic                    | >2.0                      |
| Settings         | pydantic-settings           | >=2.2.1, <3.0.0           |
| Migrations       | Alembic                     | >=1.12.1, <2.0.0          |
| Database         | PostgreSQL                  | 18 (via Docker Compose)   |
| Auth (JWT)       | PyJWT                       | >=2.8.0, <3.0.0           |
| Auth (passwords) | pwdlib[argon2,bcrypt]       | >=0.3.0                   |
| HTTP Client      | httpx                       | >=0.25.1, <1.0.0          |
| Testing          | pytest                      | >=7.4.3, <8.0.0           |
| Linting          | Ruff                        | >=0.2.2, <1.0.0           |
| Type Checking    | mypy (strict)               | >=1.8.0, <2.0.0           |
| Package Manager  | uv                          | Latest                    |
| Pre-commit       | prek                        | >=0.2.24, <1.0.0          |
| Containerization | Docker                      | Latest                    |

## Setup Commands

```bash
uv sync                              # Install dependencies from pyproject.toml
uv run fastapi dev app/main.py       # Dev server with hot reload on :8000
uv run fastapi run app/main.py       # Production server
uv run pytest                         # Run all tests
uv run mypy app/                      # Type check (strict mode)
uv run ruff check .                   # Lint
uv run ruff format .                  # Format
uv run alembic upgrade head           # Run database migrations
uv run alembic revision --autogenerate -m "description"  # Generate migration
uv run alembic downgrade -1           # Rollback one migration
uv run alembic history                # View migration history
uv add <package>                      # Add production dependency
uv add --dev <package>                # Add dev dependency
uv run prek install -f                # Install pre-commit hooks
```

## Project Structure

```
backend/
├── pyproject.toml                     # Dependencies, Ruff config, mypy config
├── alembic.ini                        # Alembic configuration
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app instance, CORS, router registration
│   ├── models.py                      # ALL SQLModel tables + Pydantic schemas (single file)
│   ├── crud.py                        # ALL database operations (flat functions, not classes)
│   ├── utils.py                       # Email utilities
│   ├── initial_data.py                # Seed script for first superuser
│   ├── backend_pre_start.py           # DB readiness check
│   ├── tests_pre_start.py             # Test DB readiness check
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings (reads ../.env)
│   │   ├── db.py                      # Sync SQLModel engine + init_db()
│   │   └── security.py                # JWT creation + password hashing (PyJWT + pwdlib)
│   ├── api/
│   │   ├── main.py                    # APIRouter aggregation
│   │   ├── deps.py                    # Dependency injection (SessionDep, CurrentUser, etc.)
│   │   └── routes/
│   │       ├── applications.py        # Citizenship app CRUD + docs + processing + review + audit
│   │       ├── users.py               # User management (admin)
│   │       ├── items.py               # Items CRUD (demo resource)
│   │       ├── login.py               # Auth endpoints (token, password reset)
│   │       ├── utils.py               # Health check, test email
│   │       └── private.py             # Dev-only routes (local environment)
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                  # Migration scripts
│   └── email-templates/               # Jinja2 email templates
├── data/
│   └── uploads/                       # File upload storage (per-application UUID dirs)
├── tests/
│   ├── conftest.py                    # Fixtures: db session, TestClient, auth token headers
│   ├── api/routes/                    # Integration tests per route module
│   │   ├── test_applications.py
│   │   ├── test_items.py
│   │   ├── test_login.py
│   │   ├── test_users.py
│   │   └── test_private.py
│   ├── crud/
│   │   └── test_user.py              # CRUD unit tests
│   ├── scripts/                       # Pre-start script tests
│   └── utils/                         # Test helper utilities
├── scripts/
│   ├── prestart.sh                    # Docker prestart (migrations + seed)
│   ├── test.sh                        # Test runner script
│   ├── tests-start.sh                 # Test startup script
│   ├── lint.sh                        # Lint script
│   └── format.sh                      # Format script
```

## Critical Conventions

### Architecture — Flat CRUD, NOT Service/Repository

This project uses a **flat architecture** — NOT the service/repository pattern:

- `app/models.py` — ALL SQLModel table definitions AND Pydantic request/response schemas in one file
- `app/crud.py` — ALL database operations as standalone functions (not classes)
- `app/api/routes/` — Route handlers that call CRUD functions directly or do inline queries
- `app/api/deps.py` — FastAPI dependency injection (session, auth)

```python
# ✅ Correct — This project's pattern: flat CRUD functions with sync sessions
from sqlmodel import Session, select
from app.models import User, UserCreate
from app.core.security import get_password_hash

def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

# ❌ Wrong — Do NOT create service classes or repository classes
# ❌ Wrong — Do NOT use async sessions (this project uses sync SQLModel)
```

### SQLModel Pattern (NOT raw SQLAlchemy)

```python
# ✅ Correct — SQLModel tables use Field() and Relationship()
import uuid
from sqlmodel import Field, Relationship, SQLModel

class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)

# ❌ Wrong — Do NOT use SQLAlchemy's Mapped[], mapped_column(), Base
# ❌ Wrong — Do NOT create separate model files; everything goes in app/models.py
```

### Schemas and Models Live Together

```python
# ✅ Correct — Pydantic schemas are SQLModel classes (without table=True) in app/models.py

# Base (shared fields)
class CitizenshipApplicationBase(SQLModel):
    applicant_full_name: str = Field(min_length=1, max_length=255)
    applicant_nationality: str = Field(min_length=1, max_length=128)

# Create schema
class CitizenshipApplicationCreate(CitizenshipApplicationBase):
    pass

# Update schema (all optional)
class CitizenshipApplicationUpdate(SQLModel):
    applicant_full_name: str | None = Field(default=None, min_length=1, max_length=255)

# Table (database model)
class CitizenshipApplication(CitizenshipApplicationBase, table=True):
    __tablename__ = "citizenship_application"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: str = Field(default=ApplicationStatus.DRAFT.value, max_length=32)
    # ...relationships, timestamps, etc.

# Public response schema
class CitizenshipApplicationPublic(CitizenshipApplicationBase):
    id: uuid.UUID
    status: ApplicationStatus
    # ...

# ❌ Wrong — Do NOT create app/schemas/ directory
# ❌ Wrong — Do NOT use plain Pydantic BaseModel; use SQLModel for everything
```

### Dependency Injection Pattern

```python
# ✅ Correct — Sync session via generator, annotated dependencies
from collections.abc import Generator
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session
from app.core.db import engine

def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]
CurrentUser = Annotated[User, Depends(get_current_user)]

# ❌ Wrong — Do NOT use AsyncSession, async_sessionmaker, or create_async_engine
```

### Route Pattern

```python
# ✅ Correct — Routes use SessionDep and CurrentUser, sync def (not async)
from app.api.deps import CurrentUser, SessionDep

router = APIRouter(prefix="/applications", tags=["applications"])

@router.get("/", response_model=CitizenshipApplicationsPublic)
def list_applications(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> CitizenshipApplicationsPublic:
    statement = select(CitizenshipApplication).where(
        CitizenshipApplication.owner_id == current_user.id
    )
    results = session.exec(statement).all()
    return CitizenshipApplicationsPublic(data=results, count=len(results))

# ❌ Wrong — Do NOT use async def for route handlers
# ❌ Wrong — Do NOT inject service classes via Depends
```

### Auth Pattern (PyJWT + pwdlib)

```python
# ✅ Correct — PyJWT for tokens, pwdlib for password hashing
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

def create_access_token(subject: str, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    return password_hash.verify_and_update(plain_password, hashed_password)

# ❌ Wrong — Do NOT use python-jose or passlib (not in this project)
```

### Configuration Pattern

```python
# ✅ Correct — Pydantic Settings reading from ../.env (one level above backend/)
from pydantic import computed_field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env", env_ignore_empty=True, extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
```

### Testing Pattern

```python
# ✅ Correct — Sync TestClient, session-scoped db fixture, module-scoped client
import pytest
from collections.abc import Generator
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.db import engine, init_db
from app.main import app

@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c

def test_create_application(
    client: TestClient, superuser_token_headers: dict[str, str]
):
    response = client.post(
        "/api/v1/applications/",
        headers=superuser_token_headers,
        json={
            "applicant_full_name": "Test User",
            "applicant_nationality": "Norwegian",
        },
    )
    assert response.status_code == 200

# ❌ Wrong — Do NOT use AsyncClient, ASGITransport, or pytest.mark.asyncio
# ❌ Wrong — Do NOT use httpx directly; use FastAPI's TestClient
```

### Naming

- **Files/Modules**: `snake_case.py`
- **Classes**: `PascalCase` (e.g., `CitizenshipApplication`, `UserCreate`)
- **Functions/Methods**: `snake_case` (e.g., `create_user`, `get_owned_application`)
- **Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `UPLOAD_ROOT`, `ALLOWED_CONTENT_TYPES`)
- **SQLModel tables**: `PascalCase` singular (`User`, `CitizenshipApplication`)
- **Pydantic schemas**: `PascalCase` with purpose suffix (`UserCreate`, `UserPublic`, `UserUpdate`)
- **Enums**: `PascalCase` class, `UPPER_SNAKE_CASE` values (`ApplicationStatus.DRAFT`)

## Domain Models

Key SQLModel tables (all in `app/models.py`):

| Model                      | Purpose                                              |
| -------------------------- | ---------------------------------------------------- |
| `User`                     | Auth users (email, hashed_password, is_superuser)    |
| `Item`                     | Demo resource (owner_id FK to User)                  |
| `CitizenshipApplication`   | Main entity — status, scores, SLA, decision fields   |
| `ApplicationDocument`      | Uploaded files (PDF/image) with OCR extraction fields |
| `EligibilityRuleResult`    | Individual rule scores with rationale and evidence   |
| `ApplicationAuditEvent`    | Immutable audit trail entries                        |

### Application Status Flow

```
draft → documents_uploaded → queued → processing → review_ready → approved | rejected | more_info_required
```

### Review Decision Actions

`approve`, `reject`, `request_more_info` — all require mandatory reason text (min 8 chars).

### File Uploads

- Storage root: `data/uploads/{application_id}/`
- Allowed MIME types: `application/pdf`, `image/jpeg`, `image/png`, `image/webp`
- Documents tracked via `ApplicationDocument` table with OCR/extraction fields

### Review Queue & SLA

- `priority_score` (0–100): ranks manual-review workload
- `sla_due_at`: deadline for reviewer action
- Queue endpoints: `GET /api/v1/applications/queue/review`, `GET /api/v1/applications/queue/metrics`
- Metrics: `pending_manual_count`, `overdue_count`, `high_priority_count`, `avg_waiting_days`

## Common Tasks

### Add a new API resource

1. Add SQLModel table + Pydantic schemas to `app/models.py`
2. Add CRUD functions to `app/crud.py` (if shared logic needed)
3. Create route file in `app/api/routes/`
4. Register router in `app/api/main.py`
5. Generate migration: `uv run alembic revision --autogenerate -m "add X table"`
6. Run migration: `uv run alembic upgrade head`
7. Write tests in `tests/api/routes/`

### Add a field to an existing model

1. Update the model class in `app/models.py`
2. Update corresponding Create/Update/Public schemas in `app/models.py`
3. Generate migration: `uv run alembic revision --autogenerate -m "add field to X"`
4. Run migration: `uv run alembic upgrade head`
5. Update tests

## PR/Commit Guidelines

- Run `uv run ruff check . && uv run ruff format . && uv run pytest` before committing
- Run `uv run mypy app/` to verify type safety
- Add/update tests for any code changes
- Include Alembic migrations for any model changes
- Title format: `[module/feature] Description`
