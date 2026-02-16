import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import EmailStr
from sqlalchemy import JSON, DateTime
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    applications: list["CitizenshipApplication"] = Relationship(
        back_populates="owner", cascade_delete=True
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    REVIEW_READY = "review_ready"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class CitizenshipApplicationBase(SQLModel):
    applicant_full_name: str = Field(min_length=1, max_length=255)
    applicant_nationality: str = Field(min_length=1, max_length=128)
    applicant_birth_date: datetime | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=2000)


class CitizenshipApplicationCreate(CitizenshipApplicationBase):
    pass


class CitizenshipApplicationUpdate(SQLModel):
    applicant_full_name: str | None = Field(default=None, min_length=1, max_length=255)
    applicant_nationality: str | None = Field(default=None, min_length=1, max_length=128)
    applicant_birth_date: datetime | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=2000)


class CitizenshipApplication(CitizenshipApplicationBase, table=True):
    __tablename__ = "citizenship_application"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: str = Field(default=ApplicationStatus.DRAFT.value, max_length=32)
    recommendation_summary: str | None = Field(default=None, max_length=2000)
    confidence_score: float | None = Field(default=None)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )

    owner: User | None = Relationship(back_populates="applications")
    documents: list["ApplicationDocument"] = Relationship(
        back_populates="application", cascade_delete=True
    )


class CitizenshipApplicationPublic(CitizenshipApplicationBase):
    id: uuid.UUID
    status: ApplicationStatus
    recommendation_summary: str | None = None
    confidence_score: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    owner_id: uuid.UUID


class CitizenshipApplicationsPublic(SQLModel):
    data: list[CitizenshipApplicationPublic]
    count: int


class ApplicationDocumentBase(SQLModel):
    document_type: str = Field(min_length=1, max_length=80)


class ApplicationDocumentCreate(ApplicationDocumentBase):
    pass


class ApplicationDocument(ApplicationDocumentBase, table=True):
    __tablename__ = "application_document"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    original_filename: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    file_size_bytes: int
    storage_path: str = Field(max_length=1024)
    status: str = Field(default=DocumentStatus.UPLOADED.value, max_length=32)
    ocr_text: str | None = Field(default=None)
    extracted_fields: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    processing_error: str | None = Field(default=None, max_length=512)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    application_id: uuid.UUID = Field(
        foreign_key="citizenship_application.id", nullable=False, ondelete="CASCADE"
    )

    application: CitizenshipApplication | None = Relationship(back_populates="documents")


class ApplicationDocumentPublic(ApplicationDocumentBase):
    id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    status: DocumentStatus
    ocr_text: str | None = None
    extracted_fields: dict[str, Any]
    processing_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    application_id: uuid.UUID


class ApplicationDocumentsPublic(SQLModel):
    data: list[ApplicationDocumentPublic]
    count: int


class ApplicationProcessRequest(SQLModel):
    force_reprocess: bool = False


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
