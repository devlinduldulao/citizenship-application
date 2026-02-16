import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from sqlmodel import Session, col, delete, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.db import engine
from app.models import (
    ApplicationDocument,
    ApplicationDocumentPublic,
    ApplicationDocumentsPublic,
    ApplicationDecisionBreakdownPublic,
    ApplicationProcessRequest,
    ApplicationStatus,
    CitizenshipApplication,
    CitizenshipApplicationCreate,
    CitizenshipApplicationPublic,
    CitizenshipApplicationsPublic,
    DocumentStatus,
    EligibilityRuleResult,
    EligibilityRuleResultPublic,
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

        statement = delete(EligibilityRuleResult).where(
            EligibilityRuleResult.application_id == application_id
        )
        session.exec(statement)

        rules = evaluate_eligibility_rules(application=application, documents=documents)
        for rule in rules:
            session.add(rule)

        weighted_score_sum = sum(rule.score * rule.weight for rule in rules)
        total_weight = sum(rule.weight for rule in rules)
        confidence_score = weighted_score_sum / total_weight if total_weight else 0
        passed_rules = sum(1 for rule in rules if rule.passed)

        risk_level = get_risk_level(confidence_score=confidence_score)
        recommendation = get_recommendation(
            confidence_score=confidence_score,
            processed_documents=processed_documents,
            failed_documents=failed_documents,
        )

        application.status = ApplicationStatus.REVIEW_READY.value
        application.recommendation_summary = (
            f"{recommendation}. "
            f"Rules passed: {passed_rules}/{len(rules)}. "
            f"Risk level: {risk_level}."
        )
        application.confidence_score = round(confidence_score, 2)
        application.updated_at = get_datetime_utc()
        session.add(application)
        session.commit()


def get_risk_level(*, confidence_score: float) -> str:
    if confidence_score >= 0.8:
        return "low"
    if confidence_score >= 0.6:
        return "medium"
    return "high"


def get_recommendation(
    *, confidence_score: float, processed_documents: int, failed_documents: int
) -> str:
    if failed_documents > 0:
        return "Manual follow-up required due to failed document parsing"
    if processed_documents == 0:
        return "Insufficient evidence for automated recommendation"
    if confidence_score >= 0.8:
        return "Eligible for fast-track manual verification"
    if confidence_score >= 0.6:
        return "Borderline eligibility; prioritize targeted human review"
    return "Likely not eligible in current submission; request additional evidence"


def evaluate_eligibility_rules(
    *, application: CitizenshipApplication, documents: list[ApplicationDocument]
) -> list[EligibilityRuleResult]:
    normalized_types = {document.document_type.strip().lower() for document in documents}
    processed_documents = [
        document for document in documents if document.status == DocumentStatus.PROCESSED.value
    ]

    has_identity_document = "passport" in normalized_types or "id_card" in normalized_types
    has_residency_document = (
        "residence_permit" in normalized_types
        or "residence_proof" in normalized_types
        or "tax_statement" in normalized_types
    )
    has_language_document = (
        "language_certificate" in normalized_types
        or "norwegian_test" in normalized_types
        or "education_certificate" in normalized_types
    )
    has_police_document = "police_clearance" in normalized_types

    ocr_quality_ratio = len(processed_documents) / len(documents) if documents else 0
    note_text = (application.notes or "").strip().lower()
    mentions_long_residency = (
        "years" in note_text
        or "permanent residence" in note_text
        or "long-term" in note_text
    )

    rule_payloads: list[dict[str, Any]] = [
        {
            "rule_code": "identity_document_present",
            "rule_name": "Identity document provided",
            "passed": has_identity_document,
            "score": 1.0 if has_identity_document else 0.0,
            "weight": 0.25,
            "rationale": (
                "Passport or national ID detected"
                if has_identity_document
                else "No passport or national ID document uploaded"
            ),
            "evidence": {"document_types": sorted(normalized_types)},
        },
        {
            "rule_code": "residency_evidence_present",
            "rule_name": "Residency evidence provided",
            "passed": has_residency_document,
            "score": 1.0 if has_residency_document else 0.0,
            "weight": 0.2,
            "rationale": (
                "Residency-related document detected"
                if has_residency_document
                else "No residency proof document detected"
            ),
            "evidence": {"document_types": sorted(normalized_types)},
        },
        {
            "rule_code": "language_requirement_evidence",
            "rule_name": "Language or integration evidence",
            "passed": has_language_document,
            "score": 1.0 if has_language_document else 0.35,
            "weight": 0.15,
            "rationale": (
                "Language/integration certificate detected"
                if has_language_document
                else "No explicit language certificate found"
            ),
            "evidence": {"document_types": sorted(normalized_types)},
        },
        {
            "rule_code": "document_parsing_quality",
            "rule_name": "Document OCR extraction quality",
            "passed": ocr_quality_ratio >= 0.8,
            "score": round(ocr_quality_ratio, 2),
            "weight": 0.25,
            "rationale": (
                "Most documents parsed successfully"
                if ocr_quality_ratio >= 0.8
                else "OCR quality is too low for confident recommendation"
            ),
            "evidence": {
                "processed_documents": len(processed_documents),
                "total_documents": len(documents),
            },
        },
        {
            "rule_code": "security_screening_signal",
            "rule_name": "Security screening evidence",
            "passed": has_police_document,
            "score": 1.0 if has_police_document else 0.4,
            "weight": 0.15,
            "rationale": (
                "Police clearance document detected"
                if has_police_document
                else "No police clearance document uploaded"
            ),
            "evidence": {"document_types": sorted(normalized_types)},
        },
    ]

    if mentions_long_residency:
        rule_payloads.append(
            {
                "rule_code": "residency_duration_signal",
                "rule_name": "Residency duration signal from case notes",
                "passed": True,
                "score": 0.8,
                "weight": 0.1,
                "rationale": "Case notes indicate long-term residence",
                "evidence": {"notes": application.notes},
            }
        )

    return [
        EligibilityRuleResult(
            application_id=application.id,
            rule_code=payload["rule_code"],
            rule_name=payload["rule_name"],
            passed=payload["passed"],
            score=payload["score"],
            weight=payload["weight"],
            rationale=payload["rationale"],
            evidence=payload["evidence"],
        )
        for payload in rule_payloads
    ]


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


@router.get(
    "/{application_id}/decision-breakdown",
    response_model=ApplicationDecisionBreakdownPublic,
)
def read_application_decision_breakdown(
    session: SessionDep, current_user: CurrentUser, application_id: uuid.UUID
) -> Any:
    application = get_owned_application(
        session=session, current_user=current_user, application_id=application_id
    )
    rules = session.exec(
        select(EligibilityRuleResult)
        .where(EligibilityRuleResult.application_id == application_id)
        .order_by(col(EligibilityRuleResult.created_at).desc())
    ).all()

    confidence_score = application.confidence_score or 0.0
    recommendation = (
        application.recommendation_summary
        or "Processing not completed yet for this application"
    )

    return ApplicationDecisionBreakdownPublic(
        application_id=application.id,
        recommendation=recommendation,
        confidence_score=round(confidence_score, 2),
        risk_level=get_risk_level(confidence_score=confidence_score),
        rules=[EligibilityRuleResultPublic.model_validate(rule) for rule in rules],
    )
