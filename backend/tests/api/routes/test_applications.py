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
