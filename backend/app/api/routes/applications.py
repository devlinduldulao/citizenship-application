import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from sqlmodel import Session, col, delete, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.db import engine
from app.models import (
    ApplicationAuditEvent,
    ApplicationAuditEventPublic,
    ApplicationAuditTrailPublic,
    ApplicationCaseExplanationPublic,
    ApplicationDecisionBreakdownPublic,
    ApplicationDocument,
    ApplicationDocumentPublic,
    ApplicationDocumentsPublic,
    ApplicationEvidenceRecommendationPublic,
    ApplicationProcessRequest,
    ApplicationStatus,
    CitizenshipApplication,
    CitizenshipApplicationCreate,
    CitizenshipApplicationPublic,
    CitizenshipApplicationsPublic,
    DocumentStatus,
    EligibilityRuleResult,
    EligibilityRuleResultPublic,
    ReviewDecisionAction,
    ReviewDecisionRequest,
    ReviewQueueItemPublic,
    ReviewQueueMetricsPublic,
    ReviewQueuePublic,
    get_datetime_utc,
)
from app.services.case_explainer import (
    generate_case_explanation,
    generate_evidence_recommendations,
)
from app.services.nlp import (
    ExtractedEntities,
    compute_document_nlp_score,
    extract_entities,
)
from app.services.ocr import extract_text

router = APIRouter(prefix="/applications", tags=["applications"])

UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "data" / "uploads"
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}

MANUAL_QUEUE_STATUSES = {
    ApplicationStatus.REVIEW_READY.value,
    ApplicationStatus.MORE_INFO_REQUIRED.value,
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


def add_audit_event(
    *,
    session: Session,
    application_id: uuid.UUID,
    action: str,
    reason: str | None,
    actor_user_id: uuid.UUID | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    audit_event = ApplicationAuditEvent(
        application_id=application_id,
        action=action,
        reason=reason,
        actor_user_id=actor_user_id,
        event_metadata=metadata or {},
    )
    session.add(audit_event)


def calculate_sla_due_at(*, risk_level: str) -> Any:
    now = get_datetime_utc()
    if risk_level == "high":
        return now + timedelta(days=7)
    if risk_level == "medium":
        return now + timedelta(days=14)
    return now + timedelta(days=21)


def calculate_priority_score(
    *, confidence_score: float, risk_level: str, failed_documents: int, age_days: float
) -> float:
    risk_component = {"high": 45, "medium": 30, "low": 15}.get(risk_level, 20)
    confidence_component = (1 - confidence_score) * 30
    failure_component = 15 if failed_documents > 0 else 0
    aging_component = min(age_days * 2, 20)
    score = risk_component + confidence_component + failure_component + aging_component
    return round(max(0, min(100, score)), 2)


def is_application_overdue(application: CitizenshipApplication) -> bool:
    if application.status not in MANUAL_QUEUE_STATUSES:
        return False
    if not application.sla_due_at:
        return False
    return application.sla_due_at < get_datetime_utc()


def map_review_queue_item(application: CitizenshipApplication) -> ReviewQueueItemPublic:
    confidence_score = application.confidence_score or 0.0
    risk_level = get_risk_level(confidence_score=confidence_score)
    return ReviewQueueItemPublic(
        id=application.id,
        applicant_full_name=application.applicant_full_name,
        applicant_nationality=application.applicant_nationality,
        status=ApplicationStatus(application.status),
        recommendation_summary=application.recommendation_summary,
        confidence_score=application.confidence_score,
        risk_level=risk_level,
        priority_score=application.priority_score,
        sla_due_at=application.sla_due_at,
        is_overdue=is_application_overdue(application),
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


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

    add_audit_event(
        session=session,
        application_id=application.id,
        action="application_created",
        reason="Application created by applicant",
        actor_user_id=current_user.id,
        metadata={
            "applicant_full_name": application.applicant_full_name,
            "applicant_nationality": application.applicant_nationality,
        },
    )
    session.commit()
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


@router.get("/queue/review", response_model=ReviewQueuePublic)
def read_review_queue(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")

    statement = select(CitizenshipApplication).where(
        col(CitizenshipApplication.status).in_(MANUAL_QUEUE_STATUSES)
    )
    queue_rows = session.exec(statement).all()

    queue_rows_sorted = sorted(
        queue_rows,
        key=lambda application: (
            not is_application_overdue(application),
            -application.priority_score,
            application.sla_due_at or get_datetime_utc(),
            application.created_at or get_datetime_utc(),
        ),
    )
    paged_rows = queue_rows_sorted[skip : skip + limit]
    return ReviewQueuePublic(
        data=[map_review_queue_item(row) for row in paged_rows],
        count=len(queue_rows_sorted),
    )


@router.get("/queue/metrics", response_model=ReviewQueueMetricsPublic)
def read_review_queue_metrics(
    session: SessionDep, current_user: CurrentUser, daily_manual_capacity: int = 20
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    if daily_manual_capacity <= 0:
        raise HTTPException(status_code=400, detail="daily_manual_capacity must be > 0")

    queue_rows = session.exec(
        select(CitizenshipApplication).where(
            col(CitizenshipApplication.status).in_(MANUAL_QUEUE_STATUSES)
        )
    ).all()

    pending_manual_count = len(queue_rows)
    overdue_count = sum(1 for row in queue_rows if is_application_overdue(row))
    high_priority_count = sum(1 for row in queue_rows if row.priority_score >= 75)

    now = get_datetime_utc()
    waiting_days = [
        max(0, (now - (row.created_at or now)).total_seconds() / 86400)
        for row in queue_rows
    ]
    avg_waiting_days = round(sum(waiting_days) / len(waiting_days), 2) if waiting_days else 0

    estimated_days_to_clear_backlog = round(
        pending_manual_count / daily_manual_capacity, 2
    )

    return ReviewQueueMetricsPublic(
        pending_manual_count=pending_manual_count,
        overdue_count=overdue_count,
        high_priority_count=high_priority_count,
        avg_waiting_days=avg_waiting_days,
        daily_manual_capacity=daily_manual_capacity,
        estimated_days_to_clear_backlog=estimated_days_to_clear_backlog,
    )


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
    add_audit_event(
        session=session,
        application_id=application.id,
        action="document_uploaded",
        reason="New document uploaded",
        actor_user_id=current_user.id,
        metadata={
            "document_type": document.document_type,
            "original_filename": document.original_filename,
            "mime_type": document.mime_type,
        },
    )
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
        add_audit_event(
            session=session,
            application_id=application.id,
            action="processing_started",
            reason="Automated pre-screening started",
            actor_user_id=None,
            metadata={"status": application.status},
        )
        session.commit()

        documents = session.exec(
            select(ApplicationDocument).where(
                ApplicationDocument.application_id == application_id
            )
        ).all()

        processed_documents = 0
        failed_documents = 0
        all_entities: list[ExtractedEntities] = []

        for document in documents:
            try:
                document.status = DocumentStatus.PROCESSING.value
                document.updated_at = get_datetime_utc()

                if not Path(document.storage_path).exists():
                    raise FileNotFoundError("Stored file no longer exists")

                # --- Real OCR extraction ---
                extraction = extract_text(
                    file_path=document.storage_path,
                    mime_type=document.mime_type or "application/pdf",
                )

                # --- Real NLP entity extraction ---
                entities = extract_entities(extraction.text)
                all_entities.append(entities)
                nlp_score = compute_document_nlp_score(entities)

                document.ocr_text = extraction.text or (
                    f"No text extracted from {document.original_filename} "
                    f"(method: {extraction.extraction_method})"
                )
                document.extracted_fields = {
                    "document_type": document.document_type,
                    "filename": document.original_filename,
                    "extraction_method": extraction.extraction_method,
                    "extraction_confidence": extraction.confidence,
                    "char_count": extraction.char_count,
                    "page_count": extraction.page_count,
                    "nlp_score": nlp_score,
                    "entities": entities.to_dict(),
                    "warnings": extraction.warnings,
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

        rules = evaluate_eligibility_rules(
            application=application,
            documents=documents,
            all_entities=all_entities,
        )
        for rule in rules:
            session.add(rule)

        weighted_score_sum = sum(rule.score * rule.weight for rule in rules)
        total_weight = sum(rule.weight for rule in rules)
        confidence_score = weighted_score_sum / total_weight if total_weight else 0
        passed_rules = sum(1 for rule in rules if rule.passed)

        risk_level = get_risk_level(confidence_score=confidence_score)
        age_days = max(
            0,
            (get_datetime_utc() - (application.created_at or get_datetime_utc())).total_seconds()
            / 86400,
        )
        priority_score = calculate_priority_score(
            confidence_score=confidence_score,
            risk_level=risk_level,
            failed_documents=failed_documents,
            age_days=age_days,
        )
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
        application.priority_score = priority_score
        application.sla_due_at = calculate_sla_due_at(risk_level=risk_level)
        application.updated_at = get_datetime_utc()
        session.add(application)
        add_audit_event(
            session=session,
            application_id=application.id,
            action="processing_completed",
            reason="Automated pre-screening completed",
            actor_user_id=None,
            metadata={
                "confidence_score": application.confidence_score,
                "risk_level": risk_level,
                "priority_score": application.priority_score,
                "sla_due_at": (
                    application.sla_due_at.isoformat() if application.sla_due_at else None
                ),
                "processed_documents": processed_documents,
                "failed_documents": failed_documents,
            },
        )
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
    *,
    application: CitizenshipApplication,
    documents: list[ApplicationDocument],
    all_entities: list[ExtractedEntities] | None = None,
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

    # --- Aggregate NLP entities across all documents ---
    merged_entities = ExtractedEntities()
    nlp_scores: list[float] = []
    if all_entities:
        for ent in all_entities:
            merged_entities.dates.extend(ent.dates)
            merged_entities.passport_numbers.extend(ent.passport_numbers)
            merged_entities.names.extend(ent.names)
            merged_entities.nationalities.extend(ent.nationalities)
            merged_entities.keywords_found.extend(ent.keywords_found)
            merged_entities.language_indicators.extend(ent.language_indicators)
            merged_entities.residency_indicators.extend(ent.residency_indicators)
            merged_entities.addresses.extend(ent.addresses)
            merged_entities.numeric_values.extend(ent.numeric_values)
            merged_entities.raw_entity_count += ent.raw_entity_count
            nlp_scores.append(compute_document_nlp_score(ent))

    avg_nlp_score = round(sum(nlp_scores) / len(nlp_scores), 2) if nlp_scores else 0.0

    # NLP-enhanced signals
    nlp_has_passport_number = len(merged_entities.passport_numbers) > 0
    nlp_has_language_signal = len(merged_entities.language_indicators) > 0
    nlp_has_residency_signal = len(merged_entities.residency_indicators) > 0

    # Boost identity score if NLP found passport numbers in text
    identity_score = 1.0 if has_identity_document else 0.0
    if nlp_has_passport_number and has_identity_document:
        identity_score = 1.0  # confirmed by content
    elif nlp_has_passport_number:
        identity_score = 0.7  # found in text but no doc type match

    # Boost residency score with NLP signals
    residency_score = 1.0 if has_residency_document else 0.0
    if nlp_has_residency_signal and not has_residency_document:
        residency_score = 0.6  # NLP found residency keywords in content

    # Boost language score with NLP signals
    language_score = 1.0 if has_language_document else 0.35
    if nlp_has_language_signal and not has_language_document:
        language_score = 0.7  # NLP found language test indicators

    rule_payloads: list[dict[str, Any]] = [
        {
            "rule_code": "identity_document_present",
            "rule_name": "Identity document provided",
            "passed": has_identity_document or nlp_has_passport_number,
            "score": identity_score,
            "weight": 0.20,
            "rationale": (
                "Passport or national ID detected"
                + ("; passport number extracted from text" if nlp_has_passport_number else "")
                if has_identity_document or nlp_has_passport_number
                else "No passport or national ID document uploaded"
            ),
            "evidence": {
                "document_types": sorted(normalized_types),
                "nlp_passport_numbers": merged_entities.passport_numbers[:3],
                "nlp_dates_found": len(merged_entities.dates),
            },
        },
        {
            "rule_code": "residency_evidence_present",
            "rule_name": "Residency evidence provided",
            "passed": has_residency_document or nlp_has_residency_signal,
            "score": residency_score,
            "weight": 0.18,
            "rationale": (
                "Residency-related document detected"
                + (
                    "; NLP found residency keywords in text"
                    if nlp_has_residency_signal
                    else ""
                )
                if has_residency_document or nlp_has_residency_signal
                else "No residency proof document or text signals detected"
            ),
            "evidence": {
                "document_types": sorted(normalized_types),
                "nlp_residency_indicators": merged_entities.residency_indicators[:5],
                "nlp_addresses": merged_entities.addresses[:3],
            },
        },
        {
            "rule_code": "language_requirement_evidence",
            "rule_name": "Language or integration evidence",
            "passed": has_language_document or nlp_has_language_signal,
            "score": language_score,
            "weight": 0.15,
            "rationale": (
                "Language/integration certificate detected"
                + (
                    "; language proficiency indicators found in text"
                    if nlp_has_language_signal
                    else ""
                )
                if has_language_document or nlp_has_language_signal
                else "No explicit language certificate or text indicators found"
            ),
            "evidence": {
                "document_types": sorted(normalized_types),
                "nlp_language_indicators": merged_entities.language_indicators[:5],
            },
        },
        {
            "rule_code": "document_parsing_quality",
            "rule_name": "Document OCR/NLP extraction quality",
            "passed": ocr_quality_ratio >= 0.8,
            "score": round(ocr_quality_ratio, 2),
            "weight": 0.17,
            "rationale": (
                f"OCR processed {len(processed_documents)}/{len(documents)} documents"
                + (f"; avg NLP entity score {avg_nlp_score}" if avg_nlp_score > 0 else "")
            ),
            "evidence": {
                "processed_documents": len(processed_documents),
                "total_documents": len(documents),
                "avg_nlp_score": avg_nlp_score,
                "total_entities_extracted": merged_entities.raw_entity_count,
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
        {
            "rule_code": "nlp_entity_richness",
            "rule_name": "NLP entity extraction richness",
            "passed": merged_entities.raw_entity_count >= 5,
            "score": min(1.0, merged_entities.raw_entity_count / 10),
            "weight": 0.10,
            "rationale": (
                f"NLP extracted {merged_entities.raw_entity_count} entities across "
                f"{len(all_entities or [])} documents "
                f"(nationalities: {len(merged_entities.nationalities)}, "
                f"keywords: {len(merged_entities.keywords_found)}, "
                f"dates: {len(merged_entities.dates)})"
            ),
            "evidence": {
                "raw_entity_count": merged_entities.raw_entity_count,
                "nationalities_found": merged_entities.nationalities[:5],
                "keywords_found": merged_entities.keywords_found[:10],
                "names_found": merged_entities.names[:3],
            },
        },
    ]

    if mentions_long_residency or nlp_has_residency_signal:
        residency_duration_score = 0.8
        if nlp_has_residency_signal and mentions_long_residency:
            residency_duration_score = 1.0
        rule_payloads.append(
            {
                "rule_code": "residency_duration_signal",
                "rule_name": "Residency duration signal",
                "passed": True,
                "score": residency_duration_score,
                "weight": 0.05,
                "rationale": (
                    "Residency duration detected via "
                    + (
                        "case notes and NLP text analysis"
                        if mentions_long_residency and nlp_has_residency_signal
                        else "case notes" if mentions_long_residency
                        else "NLP text analysis"
                    )
                ),
                "evidence": {
                    "notes": application.notes,
                    "nlp_residency_indicators": merged_entities.residency_indicators[:5],
                    "nlp_numeric_values": merged_entities.numeric_values[:5],
                },
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
    application.priority_score = 0
    application.sla_due_at = None
    application.updated_at = get_datetime_utc()
    session.add(application)
    add_audit_event(
        session=session,
        application_id=application.id,
        action="processing_queued",
        reason="Automated pre-screening queued",
        actor_user_id=current_user.id,
        metadata={"force_reprocess": process_request.force_reprocess},
    )
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


@router.get(
    "/{application_id}/case-explainer",
    response_model=ApplicationCaseExplanationPublic,
)
def read_application_case_explainer(
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
    documents = session.exec(
        select(ApplicationDocument)
        .where(ApplicationDocument.application_id == application_id)
        .order_by(col(ApplicationDocument.created_at).desc())
    ).all()
    audit_events = session.exec(
        select(ApplicationAuditEvent)
        .where(ApplicationAuditEvent.application_id == application_id)
        .order_by(col(ApplicationAuditEvent.created_at).desc())
    ).all()

    confidence_score = application.confidence_score or 0.0
    risk_level = get_risk_level(confidence_score=confidence_score)

    explanation = generate_case_explanation(
        application=application,
        rules=rules,
        documents=documents,
        audit_events=audit_events,
        risk_level=risk_level,
    )

    return ApplicationCaseExplanationPublic(
        application_id=application.id,
        summary=explanation["summary"],
        recommended_action=explanation["recommended_action"],
        key_risks=explanation["key_risks"],
        missing_evidence=explanation["missing_evidence"],
        next_steps=explanation["next_steps"],
        generated_by=explanation["generated_by"],
        generated_at=get_datetime_utc(),
    )


@router.get(
    "/{application_id}/evidence-recommendations",
    response_model=ApplicationEvidenceRecommendationPublic,
)
def read_application_evidence_recommendations(
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
    documents = session.exec(
        select(ApplicationDocument)
        .where(ApplicationDocument.application_id == application_id)
        .order_by(col(ApplicationDocument.created_at).desc())
    ).all()

    confidence_score = application.confidence_score or 0.0
    risk_level = get_risk_level(confidence_score=confidence_score)
    recommendations = generate_evidence_recommendations(
        rules=rules,
        documents=documents,
        risk_level=risk_level,
    )

    return ApplicationEvidenceRecommendationPublic(
        application_id=application.id,
        recommended_document_types=recommendations["recommended_document_types"],
        rationale_by_document_type=recommendations["rationale_by_document_type"],
        recommended_next_actions=recommendations["recommended_next_actions"],
        generated_by=recommendations["generated_by"],
        generated_at=get_datetime_utc(),
    )


@router.post("/{application_id}/review-decision", response_model=CitizenshipApplicationPublic)
def submit_review_decision(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    application_id: uuid.UUID,
    decision_in: ReviewDecisionRequest,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")

    application = get_owned_application(
        session=session, current_user=current_user, application_id=application_id
    )

    previous_status = application.status
    decision_status_map = {
        ReviewDecisionAction.APPROVE: ApplicationStatus.APPROVED.value,
        ReviewDecisionAction.REJECT: ApplicationStatus.REJECTED.value,
        ReviewDecisionAction.REQUEST_MORE_INFO: ApplicationStatus.MORE_INFO_REQUIRED.value,
    }
    final_status = decision_status_map[decision_in.action]

    application.status = final_status
    application.final_decision = final_status
    application.final_decision_reason = decision_in.reason
    application.final_decision_by_id = current_user.id
    application.final_decision_at = get_datetime_utc()
    if final_status in {
        ApplicationStatus.APPROVED.value,
        ApplicationStatus.REJECTED.value,
    }:
        application.priority_score = 0
        application.sla_due_at = None
    else:
        application.sla_due_at = get_datetime_utc() + timedelta(days=14)
        application.priority_score = max(application.priority_score, 70)
    application.updated_at = get_datetime_utc()
    session.add(application)
    add_audit_event(
        session=session,
        application_id=application.id,
        action="review_decision_submitted",
        reason=decision_in.reason,
        actor_user_id=current_user.id,
        metadata={
            "decision_action": decision_in.action.value,
            "final_status": final_status,
            "previous_status": previous_status,
        },
    )
    session.commit()
    session.refresh(application)
    return application


@router.get("/{application_id}/audit-trail", response_model=ApplicationAuditTrailPublic)
def read_application_audit_trail(
    session: SessionDep, current_user: CurrentUser, application_id: uuid.UUID
) -> Any:
    application = get_owned_application(
        session=session, current_user=current_user, application_id=application_id
    )
    events = session.exec(
        select(ApplicationAuditEvent)
        .where(ApplicationAuditEvent.application_id == application_id)
        .order_by(col(ApplicationAuditEvent.created_at).desc())
    ).all()
    return ApplicationAuditTrailPublic(
        application_id=application.id,
        events=[ApplicationAuditEventPublic.model_validate(event) for event in events],
    )
