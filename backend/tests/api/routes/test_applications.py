from fastapi.testclient import TestClient

from app.core.config import settings


def test_create_application(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    payload = {
        "applicant_full_name": "Ola Nordmann",
        "applicant_nationality": "Filipino",
        "notes": "MVP pre-screening case",
    }

    response = client.post(
        f"{settings.API_V1_STR}/applications/",
        headers=normal_user_token_headers,
        json=payload,
    )

    assert response.status_code == 200
    content = response.json()
    assert content["applicant_full_name"] == payload["applicant_full_name"]
    assert content["applicant_nationality"] == payload["applicant_nationality"]
    assert content["status"] == "draft"
    assert "id" in content


def test_upload_and_process_application(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    create_payload = {
        "applicant_full_name": "Kari Nordmann",
        "applicant_nationality": "Indian",
        "notes": "Upload and process",
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/applications/",
        headers=normal_user_token_headers,
        json=create_payload,
    )
    assert create_response.status_code == 200
    application_id = create_response.json()["id"]

    upload_response = client.post(
        f"{settings.API_V1_STR}/applications/{application_id}/documents",
        headers=normal_user_token_headers,
        data={"document_type": "passport"},
        files={
            "file": (
                "passport.pdf",
                b"%PDF-1.4 fake passport bytes",
                "application/pdf",
            )
        },
    )
    assert upload_response.status_code == 200
    upload_content = upload_response.json()
    assert upload_content["status"] == "uploaded"
    assert upload_content["document_type"] == "passport"

    process_response = client.post(
        f"{settings.API_V1_STR}/applications/{application_id}/process",
        headers=normal_user_token_headers,
        json={"force_reprocess": False},
    )
    assert process_response.status_code == 200

    application_response = client.get(
        f"{settings.API_V1_STR}/applications/{application_id}",
        headers=normal_user_token_headers,
    )
    assert application_response.status_code == 200
    application_content = application_response.json()
    assert application_content["status"] in {
        "queued",
        "processing",
        "review_ready",
    }

    documents_response = client.get(
        f"{settings.API_V1_STR}/applications/{application_id}/documents",
        headers=normal_user_token_headers,
    )
    assert documents_response.status_code == 200
    documents_content = documents_response.json()
    assert documents_content["count"] == 1
    assert documents_content["data"][0]["document_type"] == "passport"

    breakdown_response = client.get(
        f"{settings.API_V1_STR}/applications/{application_id}/decision-breakdown",
        headers=normal_user_token_headers,
    )
    assert breakdown_response.status_code == 200
    breakdown_content = breakdown_response.json()
    assert breakdown_content["application_id"] == application_id
    assert "recommendation" in breakdown_content
    assert "risk_level" in breakdown_content
    assert isinstance(breakdown_content["rules"], list)
    assert len(breakdown_content["rules"]) > 0

    queue_metrics_response = client.get(
        f"{settings.API_V1_STR}/applications/queue/metrics",
        headers=normal_user_token_headers,
    )
    assert queue_metrics_response.status_code == 403


def test_review_decision_by_superuser(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/applications/",
        headers=normal_user_token_headers,
        json={
            "applicant_full_name": "Decision Candidate",
            "applicant_nationality": "Indonesian",
            "notes": "Ready for caseworker decision",
        },
    )
    assert create_response.status_code == 200
    application_id = create_response.json()["id"]

    decision_response = client.post(
        f"{settings.API_V1_STR}/applications/{application_id}/review-decision",
        headers=superuser_token_headers,
        json={
            "action": "request_more_info",
            "reason": "Missing long-term residency proof details",
        },
    )
    assert decision_response.status_code == 200
    decision_content = decision_response.json()
    assert decision_content["status"] == "more_info_required"
    assert decision_content["final_decision"] == "more_info_required"
    assert (
        decision_content["final_decision_reason"]
        == "Missing long-term residency proof details"
    )

    audit_response = client.get(
        f"{settings.API_V1_STR}/applications/{application_id}/audit-trail",
        headers=superuser_token_headers,
    )
    assert audit_response.status_code == 200
    audit_content = audit_response.json()
    assert audit_content["application_id"] == application_id
    assert len(audit_content["events"]) > 0
    assert any(
        event["action"] == "review_decision_submitted"
        for event in audit_content["events"]
    )


def test_review_decision_requires_superuser(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/applications/",
        headers=normal_user_token_headers,
        json={
            "applicant_full_name": "Unauthorized Decision Candidate",
            "applicant_nationality": "Vietnamese",
            "notes": "Permission check",
        },
    )
    assert create_response.status_code == 200
    application_id = create_response.json()["id"]

    decision_response = client.post(
        f"{settings.API_V1_STR}/applications/{application_id}/review-decision",
        headers=normal_user_token_headers,
        json={
            "action": "approve",
            "reason": "Applicant meets all criteria",
        },
    )
    assert decision_response.status_code == 403
    assert (
        decision_response.json()["detail"]
        == "The user doesn't have enough privileges"
    )


def test_review_queue_and_metrics_for_superuser(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/applications/",
        headers=normal_user_token_headers,
        json={
            "applicant_full_name": "Queue Candidate",
            "applicant_nationality": "Thai",
            "notes": "Queue metrics coverage",
        },
    )
    assert create_response.status_code == 200
    application_id = create_response.json()["id"]

    upload_response = client.post(
        f"{settings.API_V1_STR}/applications/{application_id}/documents",
        headers=normal_user_token_headers,
        data={"document_type": "passport"},
        files={
            "file": (
                "passport.pdf",
                b"%PDF-1.4 queue candidate",
                "application/pdf",
            )
        },
    )
    assert upload_response.status_code == 200

    process_response = client.post(
        f"{settings.API_V1_STR}/applications/{application_id}/process",
        headers=normal_user_token_headers,
        json={"force_reprocess": False},
    )
    assert process_response.status_code == 200

    queue_response = client.get(
        f"{settings.API_V1_STR}/applications/queue/review",
        headers=superuser_token_headers,
    )
    assert queue_response.status_code == 200
    queue_content = queue_response.json()
    assert queue_content["count"] >= 1
    assert any(row["id"] == application_id for row in queue_content["data"])

    queue_metrics_response = client.get(
        f"{settings.API_V1_STR}/applications/queue/metrics",
        headers=superuser_token_headers,
    )
    assert queue_metrics_response.status_code == 200
    metrics_content = queue_metrics_response.json()
    assert metrics_content["pending_manual_count"] >= 1
    assert "estimated_days_to_clear_backlog" in metrics_content


def test_case_explainer_endpoint_returns_structured_response(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/applications/",
        headers=normal_user_token_headers,
        json={
            "applicant_full_name": "Explainer Candidate",
            "applicant_nationality": "Somali",
            "notes": "Need AI explainer summary",
        },
    )
    assert create_response.status_code == 200
    application_id = create_response.json()["id"]

    explainer_response = client.get(
        f"{settings.API_V1_STR}/applications/{application_id}/case-explainer",
        headers=normal_user_token_headers,
    )

    assert explainer_response.status_code == 200
    content = explainer_response.json()
    assert content["application_id"] == application_id
    assert isinstance(content["summary"], str)
    assert isinstance(content["recommended_action"], str)
    assert isinstance(content["key_risks"], list)
    assert isinstance(content["missing_evidence"], list)
    assert isinstance(content["next_steps"], list)
    assert isinstance(content["generated_by"], str)


def test_case_explainer_allows_superuser_access(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/applications/",
        headers=normal_user_token_headers,
        json={
            "applicant_full_name": "Ownership Check",
            "applicant_nationality": "Norwegian",
        },
    )
    assert create_response.status_code == 200
    application_id = create_response.json()["id"]

    superuser_response = client.get(
        f"{settings.API_V1_STR}/applications/{application_id}/case-explainer",
        headers=superuser_token_headers,
    )
    assert superuser_response.status_code == 200


def test_evidence_recommendations_endpoint_returns_expected_shape(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/applications/",
        headers=normal_user_token_headers,
        json={
            "applicant_full_name": "Evidence Candidate",
            "applicant_nationality": "Nepali",
            "notes": "Need targeted evidence suggestions",
        },
    )
    assert create_response.status_code == 200
    application_id = create_response.json()["id"]

    upload_response = client.post(
        f"{settings.API_V1_STR}/applications/{application_id}/documents",
        headers=normal_user_token_headers,
        data={"document_type": "passport"},
        files={
            "file": (
                "passport.pdf",
                b"%PDF-1.4 evidence candidate",
                "application/pdf",
            )
        },
    )
    assert upload_response.status_code == 200

    process_response = client.post(
        f"{settings.API_V1_STR}/applications/{application_id}/process",
        headers=normal_user_token_headers,
        json={"force_reprocess": False},
    )
    assert process_response.status_code == 200

    recommendation_response = client.get(
        f"{settings.API_V1_STR}/applications/{application_id}/evidence-recommendations",
        headers=normal_user_token_headers,
    )
    assert recommendation_response.status_code == 200
    content = recommendation_response.json()

    assert content["application_id"] == application_id
    assert isinstance(content["recommended_document_types"], list)
    assert isinstance(content["rationale_by_document_type"], dict)
    assert isinstance(content["recommended_next_actions"], list)
    assert isinstance(content["generated_by"], str)
