import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from sqlmodel import Session, col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.db import engine
from app.models import (
    ApplicationDocument,
    ApplicationDocumentPublic,
    ApplicationDocumentsPublic,
    ApplicationProcessRequest,
    ApplicationStatus,
    CitizenshipApplication,
    CitizenshipApplicationCreate,
    CitizenshipApplicationPublic,
    CitizenshipApplicationsPublic,
    DocumentStatus,
    get_datetime_utc,
)

router = APIRouter(prefix="/applications", tags=["applications"])

UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "data" / "uploads"
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def get_owned_application(
    *, session: SessionDep, current_user: CurrentUser, application_id: uuid.UUID
) -> CitizenshipApplication:
    application = session.get(CitizenshipApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if not current_user.is_superuser and application.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return application


@router.post("/", response_model=CitizenshipApplicationPublic)
def create_application(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    application_in: CitizenshipApplicationCreate,
) -> Any:
    application = CitizenshipApplication.model_validate(
        application_in, update={"owner_id": current_user.id}
    )
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


@router.get("/", response_model=CitizenshipApplicationsPublic)
def read_applications(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(CitizenshipApplication)
        count = session.exec(count_statement).one()
        statement = (
            select(CitizenshipApplication)
            .order_by(col(CitizenshipApplication.created_at).desc())
            .offset(skip)
            .limit(limit)
        )
    else:
        count_statement = (
            select(func.count())
            .select_from(CitizenshipApplication)
            .where(CitizenshipApplication.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(CitizenshipApplication)
            .where(CitizenshipApplication.owner_id == current_user.id)
            .order_by(col(CitizenshipApplication.created_at).desc())
            .offset(skip)
            .limit(limit)
        )

    applications = session.exec(statement).all()
    return CitizenshipApplicationsPublic(data=applications, count=count)


@router.get("/{application_id}", response_model=CitizenshipApplicationPublic)
def read_application(
    session: SessionDep, current_user: CurrentUser, application_id: uuid.UUID
) -> Any:
    return get_owned_application(
        session=session, current_user=current_user, application_id=application_id
    )


@router.post("/{application_id}/documents", response_model=ApplicationDocumentPublic)
async def upload_application_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    application_id: uuid.UUID,
    file: UploadFile = File(...),
    document_type: str = Form(...),
) -> Any:
    application = get_owned_application(
        session=session, current_user=current_user, application_id=application_id
    )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: PDF, JPEG, PNG, WEBP",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    safe_name = Path(file.filename or "uploaded-document").name
    storage_dir = UPLOAD_ROOT / str(application_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid.uuid4()}_{safe_name}"
    storage_path = storage_dir / storage_name
    storage_path.write_bytes(content)

    document = ApplicationDocument(
        application_id=application_id,
        document_type=document_type,
        original_filename=safe_name,
        mime_type=file.content_type,
        file_size_bytes=len(content),
        storage_path=str(storage_path),
    )
    application.status = ApplicationStatus.DOCUMENTS_UPLOADED.value
    application.updated_at = get_datetime_utc()

    session.add(document)
    session.add(application)
    session.commit()
    session.refresh(document)
    return document


@router.get("/{application_id}/documents", response_model=ApplicationDocumentsPublic)
def read_application_documents(
    session: SessionDep, current_user: CurrentUser, application_id: uuid.UUID
) -> Any:
    get_owned_application(
        session=session, current_user=current_user, application_id=application_id
    )

    statement = (
        select(ApplicationDocument)
        .where(ApplicationDocument.application_id == application_id)
        .order_by(col(ApplicationDocument.created_at).desc())
    )
    documents = session.exec(statement).all()
    return ApplicationDocumentsPublic(data=documents, count=len(documents))


def process_application_documents(application_id: uuid.UUID) -> None:
    with Session(engine) as session:
        application = session.get(CitizenshipApplication, application_id)
        if not application:
            return

        application.status = ApplicationStatus.PROCESSING.value
        application.updated_at = get_datetime_utc()
        session.add(application)
        session.commit()

        documents = session.exec(
            select(ApplicationDocument).where(
                ApplicationDocument.application_id == application_id
            )
        ).all()

        processed_documents = 0
        failed_documents = 0
        for document in documents:
            try:
                document.status = DocumentStatus.PROCESSING.value
                document.updated_at = get_datetime_utc()

                if not Path(document.storage_path).exists():
                    raise FileNotFoundError("Stored file no longer exists")

                document.ocr_text = (
                    "MVP OCR placeholder text extracted from "
                    f"{document.original_filename}"
                )
                document.extracted_fields = {
                    "document_type": document.document_type,
                    "filename": document.original_filename,
                    "status": "parsed",
                }
                document.processing_error = None
                document.status = DocumentStatus.PROCESSED.value
                processed_documents += 1
            except Exception as exc:
                document.status = DocumentStatus.FAILED.value
                document.processing_error = str(exc)
                failed_documents += 1
            finally:
                document.updated_at = get_datetime_utc()
                session.add(document)

        application.status = ApplicationStatus.REVIEW_READY.value
        application.recommendation_summary = (
            "MVP automated pre-screening complete. "
            f"Processed documents: {processed_documents}, failed: {failed_documents}."
        )
        application.confidence_score = 0.65
        application.updated_at = get_datetime_utc()
        session.add(application)
        session.commit()


@router.post("/{application_id}/process", response_model=CitizenshipApplicationPublic)
def queue_application_processing(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    application_id: uuid.UUID,
    process_request: ApplicationProcessRequest,
) -> Any:
    application = get_owned_application(
        session=session, current_user=current_user, application_id=application_id
    )

    documents = session.exec(
        select(ApplicationDocument).where(ApplicationDocument.application_id == application_id)
    ).all()
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="Upload at least one document before processing",
        )

    if process_request.force_reprocess:
        for document in documents:
            document.status = DocumentStatus.UPLOADED.value
            document.ocr_text = None
            document.extracted_fields = {}
            document.processing_error = None
            document.updated_at = get_datetime_utc()
            session.add(document)

    application.status = ApplicationStatus.QUEUED.value
    application.updated_at = get_datetime_utc()
    session.add(application)
    session.commit()
    session.refresh(application)

    background_tasks.add_task(process_application_documents, application_id)
    return application
