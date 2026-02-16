# FastAPI Demo — Agent Instructions

> IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any tasks in this project.

## Tech Stack

| Category         | Technology            | Version      |
| ---------------- | --------------------- | ------------ |
| Language         | Python                | 3.14.x       |
| Framework        | FastAPI               | 0.115.x      |
| ASGI Server      | Uvicorn               | 0.34.x       |
| Validation       | Pydantic              | 2.11.x       |
| ORM              | SQLAlchemy            | 2.0.x        |
| Migrations       | Alembic               | 1.15.x       |
| Database         | PostgreSQL / SQLite   | Latest       |
| Authentication   | python-jose + passlib | Latest       |
| Testing          | pytest + httpx        | 8.x + 0.28.x |
| Package Manager  | uv                    | 0.7.x        |
| Linting          | Ruff                  | 0.9.x        |
| Type Checking    | mypy / pyright        | Latest       |
| Task Queue       | Celery / ARQ          | Latest       |
| Containerization | Docker                | Latest       |

## Setup Commands

```bash
uv sync                          # Install dependencies from pyproject.toml
uv run fastapi dev                # Start dev server (hot reload, port 8000)
uv run fastapi run                # Start production server
uv run pytest                     # Run all tests
uv run pytest --cov=app           # Run tests with coverage
uv run mypy app/                  # Type check
uv run ruff check .               # Lint check
uv run ruff format .              # Format code
uv run alembic upgrade head       # Run database migrations
uv run alembic revision --autogenerate -m "description"  # Generate migration
uv add <package>                  # Add dependency
uv add --dev <package>            # Add dev dependency
```

## Project Structure

```
project-root/
├── pyproject.toml                 # Project config, dependencies, tool settings
├── uv.lock                       # Lock file (do NOT edit manually)
├── alembic.ini                    # Alembic config
├── alembic/                       # Migration scripts
│   ├── env.py
│   └── versions/
├── app/                           # Application package
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory, lifespan
│   ├── config.py                  # Settings via pydantic-settings
│   ├── database.py                # SQLAlchemy engine + session factory
│   ├── dependencies.py            # Shared FastAPI dependencies
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                # Declarative base + mixins
│   │   ├── user.py
│   │   └── item.py
│   ├── schemas/                   # Pydantic schemas (request/response)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   ├── routers/                   # API route modules
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── items.py
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── item_service.py
│   ├── repositories/              # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py                # Generic CRUD repository
│   │   └── user_repository.py
│   └── middleware/                 # Custom middleware
│       ├── __init__.py
│       └── logging.py
├── tests/                         # Test package
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures
│   ├── test_users.py              # Router/integration tests
│   ├── test_user_service.py       # Service unit tests
│   └── factories.py               # Test data factories
└── scripts/                       # Utility scripts
    └── seed_db.py
```

## Critical Conventions

### Naming

- **Files/Modules**: `snake_case.py` (e.g., `user_service.py`, `item_repository.py`)
- **Classes**: `PascalCase` (e.g., `UserService`, `ItemSchema`)
- **Functions/Methods**: `snake_case` (e.g., `get_user_by_id`, `create_item`)
- **Variables**: `snake_case` (NEVER `camelCase`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_PAGE_SIZE`)
- **Pydantic Models**: `PascalCase` with purpose suffix (`UserCreate`, `UserResponse`, `UserUpdate`)
- **SQLAlchemy Models**: `PascalCase` singular noun (`User`, `Item`, `Order`)
- **Endpoints**: `snake_case` paths (e.g., `/api/v1/user_profiles`)
- **Type aliases**: `PascalCase` (e.g., `UserId = int`)

### Python 3.14 Key Features

```python
# ✅ Template strings (PEP 750) — t-strings for safe string processing
from string.templatelib import Template

name = "world"
template = t"Hello, {name}!"  # Returns Template object, NOT a string

# ✅ Deferred evaluation of annotations (PEP 649)
# No more need for `from __future__ import annotations`
# Forward references work natively
class Node:
    def __init__(self, value: int, next: Node | None = None):  # Just works!
        self.value = value
        self.next = next

# ✅ Multiple interpreters (PEP 734)
from concurrent.interpreters import Interpreter, create

# ✅ Free-threaded mode is officially supported (PEP 779)
# No GIL for true multi-core parallelism

# ✅ except without parentheses (PEP 758)
try:
    do_something()
except ValueError, TypeError:  # No need for (ValueError, TypeError)
    handle_error()
```

### FastAPI Route Pattern

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ✅ Dependency injection via Depends()
def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(session)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.create(data)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.update(user_id, data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
```

### Pydantic Schema Pattern

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ✅ Separate schemas for Create, Update, Response
class UserBase(BaseModel):
    """Shared fields — base class is never used directly."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    """Fields required when creating a user."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """All fields optional for partial updates (PATCH)."""
    name: str | None = None
    email: EmailStr | None = None


class UserResponse(UserBase):
    """Fields returned to the client — NEVER expose passwords."""
    id: int
    created_at: datetime

    # ✅ Pydantic v2: model_config replaces class Config
    model_config = ConfigDict(from_attributes=True)
```

### SQLAlchemy Model Pattern

```python
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    # ✅ SQLAlchemy 2.0 Mapped types (not Column)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r})"
```

### Service Pattern

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Business logic for user operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def create(self, data: UserCreate) -> User:
        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def update(self, user_id: int, data: UserUpdate) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        # ✅ Pydantic v2: model_dump(exclude_unset=True) for partial updates
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        result = await self._session.execute(
            select(User).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
```

### Dependency Injection Pattern

```python
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings


# ✅ Settings cached with lru_cache
@lru_cache
def get_settings() -> Settings:
    return Settings()


# ✅ Async engine + session factory
engine = create_async_engine(get_settings().database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


# ✅ Session dependency — yields for proper cleanup
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

### Configuration via pydantic-settings

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ✅ pydantic-settings reads from .env automatically
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "FastAPI Demo"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:3000"]
```

### Testing Pattern

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.database import get_session
from app.config import Settings


# ✅ Async test fixtures with pytest-asyncio
@pytest.fixture
async def app():
    """Create app instance for testing."""
    return create_app()


@pytest.fixture
async def client(app) -> AsyncClient:
    """Async test client using httpx."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ✅ Integration test — tests the full HTTP pipeline
@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/users/",
        json={"name": "John", "email": "john@example.com", "password": "securepass123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John"
    assert data["email"] == "john@example.com"
    assert "password" not in data  # Never leak password


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    response = await client.get("/api/v1/users/99999")
    assert response.status_code == 404


# ✅ Service unit test — mock the database session
@pytest.mark.asyncio
async def test_user_service_create(mock_session):
    from app.services.user_service import UserService
    from app.schemas.user import UserCreate

    service = UserService(mock_session)
    data = UserCreate(name="Jane", email="jane@example.com", password="securepass123")

    user = await service.create(data)
    assert user.name == "Jane"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
```

## Common Tasks

### Add a new API resource

1. Create SQLAlchemy model in `app/models/`
2. Create Pydantic schemas in `app/schemas/` (Create, Update, Response)
3. Create service in `app/services/` with business logic
4. Create router in `app/routers/` with endpoints
5. Register router in `app/main.py`
6. Generate Alembic migration: `uv run alembic revision --autogenerate -m "add X table"`
7. Run migration: `uv run alembic upgrade head`
8. Write tests in `tests/`

### Add a new dependency

```bash
uv add <package>           # Production dependency
uv add --dev <package>     # Development dependency
```

### Generate Alembic migration

```bash
uv run alembic revision --autogenerate -m "add user roles"
uv run alembic upgrade head
uv run alembic downgrade -1   # Rollback one migration
uv run alembic history        # View migration history
```

## Detailed Documentation

| Topic                  | Reference                                                               |
| ---------------------- | ----------------------------------------------------------------------- |
| FastAPI Docs           | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)                   |
| Pydantic v2            | [docs.pydantic.dev](https://docs.pydantic.dev/latest/)                  |
| SQLAlchemy 2.0         | [docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/20/)               |
| Alembic                | [alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/)               |
| uv Package Manager     | [docs.astral.sh/uv](https://docs.astral.sh/uv/)                         |
| Ruff Linter            | [docs.astral.sh/ruff](https://docs.astral.sh/ruff/)                     |
| Python 3.14 What's New | [docs.python.org](https://docs.python.org/3.14/whatsnew/3.14.html)      |
| pytest-asyncio         | [pytest-asyncio.readthedocs.io](https://pytest-asyncio.readthedocs.io/) |
| httpx                  | [www.python-httpx.org](https://www.python-httpx.org/)                   |

## PR/Commit Guidelines

- Run `uv run ruff check . && uv run pytest` before committing
- Add/update tests for any code changes
- Run `uv run mypy app/` to verify type safety
- Use descriptive commit messages
- Title format: `[module/feature] Description`
- Ensure Alembic migrations are included for any model changes
