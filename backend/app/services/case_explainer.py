import json
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import settings

if TYPE_CHECKING:
    from app.models import (
        ApplicationAuditEvent,
        ApplicationDocument,
        CitizenshipApplication,
        EligibilityRuleResult,
    )


def generate_case_explanation(
    *,
    application: "CitizenshipApplication",
    rules: list["EligibilityRuleResult"],
    documents: list["ApplicationDocument"],
    audit_events: list["ApplicationAuditEvent"],
    risk_level: str,
) -> dict[str, Any]:
    fallback = _build_fallback_explanation(
        application=application,
        rules=rules,
        documents=documents,
        risk_level=risk_level,
    )

    if not _llm_enabled():
        return fallback

    try:
        llm_output = _request_llm_explanation(
            application=application,
            rules=rules,
            documents=documents,
            audit_events=audit_events,
            risk_level=risk_level,
        )
        return {
            "summary": llm_output.get("summary") or fallback["summary"],
            "recommended_action": llm_output.get("recommended_action")
            or fallback["recommended_action"],
            "key_risks": _as_string_list(
                llm_output.get("key_risks"), fallback["key_risks"]
            ),
            "missing_evidence": _as_string_list(
                llm_output.get("missing_evidence"), fallback["missing_evidence"]
            ),
            "next_steps": _as_string_list(
                llm_output.get("next_steps"), fallback["next_steps"]
            ),
            "generated_by": f"llm:{settings.AI_EXPLAINER_MODEL}",
        }
    except Exception:
        return fallback


def generate_evidence_recommendations(
    *,
    rules: list["EligibilityRuleResult"],
    documents: list["ApplicationDocument"],
    risk_level: str,
) -> dict[str, Any]:
    uploaded_types = {document.document_type.strip().lower() for document in documents}
    failed_rules = {rule.rule_code: rule for rule in rules if not rule.passed}

    rule_to_document_options: dict[str, list[str]] = {
        "identity_document_present": ["passport", "id_card"],
        "residency_evidence_present": [
            "residence_permit",
            "residence_proof",
            "tax_statement",
        ],
        "language_requirement_evidence": [
            "language_certificate",
            "norwegian_test",
            "education_certificate",
        ],
        "security_screening_signal": ["police_clearance"],
    }

    recommended_document_types: list[str] = []
    rationale_by_document_type: dict[str, str] = {}

    for rule_code, candidate_document_types in rule_to_document_options.items():
        failed_rule = failed_rules.get(rule_code)
        if not failed_rule:
            continue
        for document_type in candidate_document_types:
            if document_type in uploaded_types:
                continue
            if document_type not in recommended_document_types:
                recommended_document_types.append(document_type)
            rationale_by_document_type[document_type] = failed_rule.rationale

    recommended_next_actions = [
        "Request only high-impact missing documents first",
        "Re-run processing after document upload",
        "Review updated rule breakdown before final decision",
    ]

    if risk_level == "high":
        recommended_next_actions.insert(0, "Prioritize this application for immediate reviewer follow-up")
    elif risk_level == "medium":
        recommended_next_actions.insert(0, "Schedule targeted reviewer check after top missing evidence arrives")

    return {
        "recommended_document_types": recommended_document_types,
        "rationale_by_document_type": rationale_by_document_type,
        "recommended_next_actions": recommended_next_actions[:4],
        "generated_by": "fallback:evidence-recommendation-v1",
    }


def _build_fallback_explanation(
    *,
    application: "CitizenshipApplication",
    rules: list["EligibilityRuleResult"],
    documents: list["ApplicationDocument"],
    risk_level: str,
) -> dict[str, Any]:
    failed_rules = [rule for rule in rules if not rule.passed]
    failed_rules_sorted = sorted(
        failed_rules,
        key=lambda rule: (rule.weight, 1 - rule.score),
        reverse=True,
    )

    key_risks = [rule.rule_name for rule in failed_rules_sorted[:3]]
    if not key_risks:
        key_risks = ["No critical rule failures detected"]

    missing_evidence = [rule.rationale for rule in failed_rules_sorted[:3]]
    if not missing_evidence:
        missing_evidence = ["No material evidence gaps identified"]

    recommended_action = _recommend_action(
        status=application.status,
        risk_level=risk_level,
        failed_rules=failed_rules,
    )
    document_types = sorted({document.document_type.strip().lower() for document in documents})

    next_steps = [
        "Validate identity details against uploaded evidence",
        "Confirm residency and language requirements against policy checklist",
        "Capture final caseworker reason before decision submission",
    ]

    if "police_clearance" not in document_types:
        next_steps.insert(0, "Request police clearance evidence for security screening")
    if "residence_permit" not in document_types and "residence_proof" not in document_types:
        next_steps.insert(0, "Request residency proof document")

    summary = (
        f"Application {application.id} is currently {risk_level} risk with "
        f"{len(failed_rules)} rule gaps. Prioritize evidence validation and a "
        "documented human decision."
    )

    return {
        "summary": summary,
        "recommended_action": recommended_action,
        "key_risks": key_risks,
        "missing_evidence": missing_evidence,
        "next_steps": next_steps[:4],
        "generated_by": "fallback:rules-v1",
    }


def _recommend_action(
    *, status: str, risk_level: str, failed_rules: list["EligibilityRuleResult"]
) -> str:
    from app.models import ApplicationStatus

    if status in {
        ApplicationStatus.APPROVED.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.MORE_INFO_REQUIRED.value,
    }:
        return "no_action_finalized"

    failed_codes = {rule.rule_code for rule in failed_rules}
    if risk_level == "high":
        return "request_more_info"
    if "security_screening_signal" in failed_codes or "residency_evidence_present" in failed_codes:
        return "request_more_info"
    if risk_level == "medium":
        return "manual_review_priority"
    return "approve_with_verification"


def _llm_enabled() -> bool:
    return bool(settings.AI_EXPLAINER_API_KEY and settings.AI_EXPLAINER_BASE_URL)


def _request_llm_explanation(
    *,
    application: "CitizenshipApplication",
    rules: list["EligibilityRuleResult"],
    documents: list["ApplicationDocument"],
    audit_events: list["ApplicationAuditEvent"],
    risk_level: str,
) -> dict[str, Any]:
    context = {
        "application": {
            "id": str(application.id),
            "status": application.status,
            "applicant_full_name": application.applicant_full_name,
            "applicant_nationality": application.applicant_nationality,
            "recommendation_summary": application.recommendation_summary,
            "confidence_score": application.confidence_score,
            "risk_level": risk_level,
            "notes": application.notes,
        },
        "rules": [
            {
                "rule_code": rule.rule_code,
                "rule_name": rule.rule_name,
                "passed": rule.passed,
                "score": rule.score,
                "weight": rule.weight,
                "rationale": rule.rationale,
            }
            for rule in rules
        ],
        "documents": [
            {
                "document_type": document.document_type,
                "status": document.status,
                "mime_type": document.mime_type,
                "processing_error": document.processing_error,
            }
            for document in documents
        ],
        "audit_events": [
            {
                "action": event.action,
                "reason": event.reason,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in audit_events[:6]
        ],
    }

    payload = {
        "model": settings.AI_EXPLAINER_MODEL,
        "temperature": settings.AI_EXPLAINER_TEMPERATURE,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an immigration case assistant. Return strict JSON with keys: "
                    "summary, recommended_action, key_risks, missing_evidence, next_steps. "
                    "Keep output concise, factual, and grounded in provided evidence."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context, default=str),
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.AI_EXPLAINER_API_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=settings.AI_EXPLAINER_TIMEOUT_SECONDS) as client:
        response = client.post(
            f"{settings.AI_EXPLAINER_BASE_URL.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    content = body["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response is not a JSON object")
    return parsed


def _as_string_list(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return normalized[:5] if normalized else fallback
