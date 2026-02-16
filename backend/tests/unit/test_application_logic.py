"""Unit tests for pure business logic functions in the applications module.

These tests exercise the eligibility engine, scoring, risk, and SLA
helper functions WITHOUT requiring a database connection.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.api.routes.applications import (
    calculate_priority_score,
    calculate_sla_due_at,
    evaluate_eligibility_rules,
    get_recommendation,
    get_risk_level,
    is_application_overdue,
)
from app.models import (
    ApplicationDocument,
    ApplicationStatus,
    CitizenshipApplication,
    DocumentStatus,
)


# ---------------------------------------------------------------------------
# get_risk_level
# ---------------------------------------------------------------------------
class TestGetRiskLevel:
    def test_high_confidence_returns_low(self) -> None:
        assert get_risk_level(confidence_score=0.95) == "low"

    def test_boundary_low(self) -> None:
        assert get_risk_level(confidence_score=0.8) == "low"

    def test_medium_range(self) -> None:
        assert get_risk_level(confidence_score=0.7) == "medium"

    def test_boundary_medium(self) -> None:
        assert get_risk_level(confidence_score=0.6) == "medium"

    def test_low_confidence_returns_high(self) -> None:
        assert get_risk_level(confidence_score=0.3) == "high"

    def test_zero_confidence(self) -> None:
        assert get_risk_level(confidence_score=0.0) == "high"

    def test_just_below_medium(self) -> None:
        assert get_risk_level(confidence_score=0.59) == "high"

    def test_just_below_low(self) -> None:
        assert get_risk_level(confidence_score=0.79) == "medium"

    def test_perfect_confidence(self) -> None:
        assert get_risk_level(confidence_score=1.0) == "low"


# ---------------------------------------------------------------------------
# get_recommendation
# ---------------------------------------------------------------------------
class TestGetRecommendation:
    def test_failed_documents_override(self) -> None:
        result = get_recommendation(
            confidence_score=0.9, processed_documents=5, failed_documents=1
        )
        assert "failed document" in result.lower()

    def test_no_processed_documents(self) -> None:
        result = get_recommendation(
            confidence_score=0.9, processed_documents=0, failed_documents=0
        )
        assert "insufficient" in result.lower()

    def test_high_confidence_fast_track(self) -> None:
        result = get_recommendation(
            confidence_score=0.85, processed_documents=3, failed_documents=0
        )
        assert "fast-track" in result.lower()

    def test_medium_confidence_borderline(self) -> None:
        result = get_recommendation(
            confidence_score=0.65, processed_documents=2, failed_documents=0
        )
        assert "borderline" in result.lower()

    def test_low_confidence_not_eligible(self) -> None:
        result = get_recommendation(
            confidence_score=0.3, processed_documents=2, failed_documents=0
        )
        assert "not eligible" in result.lower() or "additional evidence" in result.lower()

    def test_boundary_at_0_8(self) -> None:
        result = get_recommendation(
            confidence_score=0.8, processed_documents=1, failed_documents=0
        )
        assert "fast-track" in result.lower()

    def test_boundary_at_0_6(self) -> None:
        result = get_recommendation(
            confidence_score=0.6, processed_documents=1, failed_documents=0
        )
        assert "borderline" in result.lower()

    def test_failed_documents_takes_precedence_over_zero_processed(self) -> None:
        result = get_recommendation(
            confidence_score=0.5, processed_documents=0, failed_documents=2
        )
        assert "failed document" in result.lower()


# ---------------------------------------------------------------------------
# calculate_priority_score
# ---------------------------------------------------------------------------
class TestCalculatePriorityScore:
    def test_high_risk_high_uncertainty(self) -> None:
        score = calculate_priority_score(
            confidence_score=0.2,
            risk_level="high",
            failed_documents=1,
            age_days=15,
        )
        # risk=45 + confidence=(1-0.2)*30=24 + failure=15 + aging=min(30,20)=20 = 104 → clamped 100
        assert score == 100

    def test_low_risk_high_confidence(self) -> None:
        score = calculate_priority_score(
            confidence_score=0.95,
            risk_level="low",
            failed_documents=0,
            age_days=0,
        )
        # risk=15 + confidence=(1-0.95)*30=1.5 + failure=0 + aging=0 = 16.5
        assert score == 16.5

    def test_medium_risk_moderate(self) -> None:
        score = calculate_priority_score(
            confidence_score=0.7,
            risk_level="medium",
            failed_documents=0,
            age_days=3,
        )
        # risk=30 + confidence=(1-0.7)*30=9 + failure=0 + aging=min(6,20)=6 = 45
        assert score == 45

    def test_score_clamped_at_zero(self) -> None:
        # This shouldn't happen with real data, but test the floor
        score = calculate_priority_score(
            confidence_score=1.0,
            risk_level="low",
            failed_documents=0,
            age_days=0,
        )
        # risk=15 + confidence=0 + failure=0 + aging=0 = 15
        assert score >= 0

    def test_aging_capped_at_20(self) -> None:
        score_10_days = calculate_priority_score(
            confidence_score=0.5,
            risk_level="medium",
            failed_documents=0,
            age_days=10,
        )
        score_100_days = calculate_priority_score(
            confidence_score=0.5,
            risk_level="medium",
            failed_documents=0,
            age_days=100,
        )
        # Aging contribution caps at 20 so both should give the same score
        assert score_10_days == score_100_days

    def test_failed_documents_add_15(self) -> None:
        score_no_fail = calculate_priority_score(
            confidence_score=0.5,
            risk_level="medium",
            failed_documents=0,
            age_days=0,
        )
        score_with_fail = calculate_priority_score(
            confidence_score=0.5,
            risk_level="medium",
            failed_documents=3,
            age_days=0,
        )
        assert score_with_fail - score_no_fail == 15

    def test_unknown_risk_level_default(self) -> None:
        score = calculate_priority_score(
            confidence_score=0.5,
            risk_level="unknown",
            failed_documents=0,
            age_days=0,
        )
        # risk_component for unknown = 20
        # risk=20 + confidence=15 + failure=0 + aging=0 = 35
        assert score == 35

    def test_return_type_is_float(self) -> None:
        score = calculate_priority_score(
            confidence_score=0.5,
            risk_level="high",
            failed_documents=0,
            age_days=1,
        )
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# calculate_sla_due_at
# ---------------------------------------------------------------------------
class TestCalculateSlaDueAt:
    def test_high_risk_7_days(self) -> None:
        before = datetime.now(timezone.utc)
        result = calculate_sla_due_at(risk_level="high")
        after = datetime.now(timezone.utc)
        assert before + timedelta(days=7) <= result <= after + timedelta(days=7)

    def test_medium_risk_14_days(self) -> None:
        before = datetime.now(timezone.utc)
        result = calculate_sla_due_at(risk_level="medium")
        after = datetime.now(timezone.utc)
        assert before + timedelta(days=14) <= result <= after + timedelta(days=14)

    def test_low_risk_21_days(self) -> None:
        before = datetime.now(timezone.utc)
        result = calculate_sla_due_at(risk_level="low")
        after = datetime.now(timezone.utc)
        assert before + timedelta(days=21) <= result <= after + timedelta(days=21)

    def test_unknown_risk_defaults_to_21_days(self) -> None:
        before = datetime.now(timezone.utc)
        result = calculate_sla_due_at(risk_level="something_else")
        after = datetime.now(timezone.utc)
        assert before + timedelta(days=21) <= result <= after + timedelta(days=21)


# ---------------------------------------------------------------------------
# is_application_overdue
# ---------------------------------------------------------------------------
def _make_application(
    *,
    status: str = ApplicationStatus.REVIEW_READY.value,
    sla_due_at: datetime | None = None,
) -> CitizenshipApplication:
    """Build a minimal CitizenshipApplication for unit testing."""
    return CitizenshipApplication(
        id=uuid.uuid4(),
        applicant_full_name="Test User",
        applicant_nationality="Norwegian",
        status=status,
        sla_due_at=sla_due_at,
        owner_id=uuid.uuid4(),
    )


class TestIsApplicationOverdue:
    def test_overdue_when_past_sla(self) -> None:
        app = _make_application(
            status=ApplicationStatus.REVIEW_READY.value,
            sla_due_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert is_application_overdue(app) is True

    def test_not_overdue_when_future_sla(self) -> None:
        app = _make_application(
            status=ApplicationStatus.REVIEW_READY.value,
            sla_due_at=datetime.now(timezone.utc) + timedelta(days=5),
        )
        assert is_application_overdue(app) is False

    def test_not_overdue_when_no_sla(self) -> None:
        app = _make_application(
            status=ApplicationStatus.REVIEW_READY.value,
            sla_due_at=None,
        )
        assert is_application_overdue(app) is False

    def test_not_overdue_when_wrong_status(self) -> None:
        app = _make_application(
            status=ApplicationStatus.DRAFT.value,
            sla_due_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert is_application_overdue(app) is False

    def test_overdue_more_info_required(self) -> None:
        app = _make_application(
            status=ApplicationStatus.MORE_INFO_REQUIRED.value,
            sla_due_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert is_application_overdue(app) is True

    def test_not_overdue_approved_status(self) -> None:
        app = _make_application(
            status=ApplicationStatus.APPROVED.value,
            sla_due_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        assert is_application_overdue(app) is False

    def test_not_overdue_rejected_status(self) -> None:
        app = _make_application(
            status=ApplicationStatus.REJECTED.value,
            sla_due_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        assert is_application_overdue(app) is False


# ---------------------------------------------------------------------------
# evaluate_eligibility_rules
# ---------------------------------------------------------------------------
def _make_document(
    application_id: uuid.UUID,
    document_type: str,
    *,
    status: str = DocumentStatus.PROCESSED.value,
) -> ApplicationDocument:
    return ApplicationDocument(
        id=uuid.uuid4(),
        application_id=application_id,
        document_type=document_type,
        original_filename=f"{document_type}.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        storage_path=f"/tmp/{document_type}.pdf",
        status=status,
    )


class TestEvaluateEligibilityRules:
    def test_passport_triggers_identity_rule(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "passport")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        identity_rule = next(r for r in rules if r.rule_code == "identity_document_present")
        assert identity_rule.passed is True
        assert identity_rule.score == 1.0

    def test_no_identity_document_fails_rule(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "tax_statement")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        identity_rule = next(r for r in rules if r.rule_code == "identity_document_present")
        assert identity_rule.passed is False
        assert identity_rule.score == 0.0

    def test_residency_evidence_detected(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "residence_permit")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        residency_rule = next(r for r in rules if r.rule_code == "residency_evidence_present")
        assert residency_rule.passed is True

    def test_language_certificate_detected(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "language_certificate")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        lang_rule = next(r for r in rules if r.rule_code == "language_requirement_evidence")
        assert lang_rule.passed is True
        assert lang_rule.score == 1.0

    def test_no_language_document_partial_score(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "passport")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        lang_rule = next(r for r in rules if r.rule_code == "language_requirement_evidence")
        assert lang_rule.passed is False
        assert lang_rule.score == 0.35

    def test_police_clearance_security_rule(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "police_clearance")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        security_rule = next(r for r in rules if r.rule_code == "security_screening_signal")
        assert security_rule.passed is True
        assert security_rule.score == 1.0

    def test_no_police_clearance_partial_score(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "passport")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        security_rule = next(r for r in rules if r.rule_code == "security_screening_signal")
        assert security_rule.passed is False
        assert security_rule.score == 0.4

    def test_ocr_quality_all_processed(self) -> None:
        app = _make_application()
        docs = [
            _make_document(app.id, "passport", status=DocumentStatus.PROCESSED.value),
            _make_document(app.id, "tax_statement", status=DocumentStatus.PROCESSED.value),
        ]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        ocr_rule = next(r for r in rules if r.rule_code == "document_parsing_quality")
        assert ocr_rule.passed is True
        assert ocr_rule.score == 1.0

    def test_ocr_quality_mixed_status(self) -> None:
        app = _make_application()
        docs = [
            _make_document(app.id, "passport", status=DocumentStatus.PROCESSED.value),
            _make_document(app.id, "tax_statement", status=DocumentStatus.FAILED.value),
        ]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        ocr_rule = next(r for r in rules if r.rule_code == "document_parsing_quality")
        assert ocr_rule.passed is False
        assert ocr_rule.score == 0.5

    def test_long_residency_bonus_rule_present(self) -> None:
        app = _make_application()
        app.notes = "Applicant has lived in Norway for 10 years as permanent resident"
        docs = [_make_document(app.id, "passport")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        residency_duration_rules = [
            r for r in rules if r.rule_code == "residency_duration_signal"
        ]
        assert len(residency_duration_rules) == 1
        assert residency_duration_rules[0].passed is True
        assert residency_duration_rules[0].score == 0.8

    def test_no_residency_mention_no_bonus_rule(self) -> None:
        app = _make_application()
        app.notes = "Standard application"
        docs = [_make_document(app.id, "passport")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        residency_duration_rules = [
            r for r in rules if r.rule_code == "residency_duration_signal"
        ]
        assert len(residency_duration_rules) == 0

    def test_empty_documents_list(self) -> None:
        app = _make_application()
        rules = evaluate_eligibility_rules(application=app, documents=[])
        assert len(rules) == 6  # base rules always present (includes nlp_entity_richness)
        # All should fail or have zero scores
        identity_rule = next(r for r in rules if r.rule_code == "identity_document_present")
        assert identity_rule.passed is False

    def test_weights_sum_close_to_one(self) -> None:
        """Base rules weights should sum to ~0.95 (residency_duration_signal adds 0.05 conditionally)."""
        app = _make_application()
        docs = [_make_document(app.id, "passport")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        base_rules = [r for r in rules if r.rule_code != "residency_duration_signal"]
        total_weight = sum(r.weight for r in base_rules)
        assert total_weight == pytest.approx(0.95, abs=0.01)

    def test_all_documents_create_strong_case(self) -> None:
        """Full document set should produce high scores across all doc-type rules."""
        app = _make_application()
        app.notes = "Long-term resident for 12 years"
        docs = [
            _make_document(app.id, "passport"),
            _make_document(app.id, "residence_permit"),
            _make_document(app.id, "language_certificate"),
            _make_document(app.id, "police_clearance"),
        ]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        # nlp_entity_richness may not pass without real OCR text, exclude it
        doc_type_rules = [r for r in rules if r.rule_code != "nlp_entity_richness"]
        assert all(r.passed for r in doc_type_rules)
        assert len(rules) == 7  # 6 base + 1 bonus (residency_duration_signal)

    def test_id_card_also_satisfies_identity(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "id_card")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        identity_rule = next(r for r in rules if r.rule_code == "identity_document_present")
        assert identity_rule.passed is True

    def test_document_type_case_insensitive(self) -> None:
        app = _make_application()
        docs = [_make_document(app.id, "  Passport  ")]
        rules = evaluate_eligibility_rules(application=app, documents=docs)
        identity_rule = next(r for r in rules if r.rule_code == "identity_document_present")
        assert identity_rule.passed is True
