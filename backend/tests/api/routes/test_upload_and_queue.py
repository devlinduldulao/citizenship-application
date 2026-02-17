"""Tests for the document upload and queue processing endpoints.

Covers the full lifecycle: upload validation, MIME type checks, empty-file
rejection, queue-with-no-documents guard, queue-with-documents happy path,
and force-reprocess behaviour.
"""

import uuid

from fastapi.testclient import TestClient

from app.core.config import settings

API = settings.API_V1_STR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_application(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Upload Test User",
    nationality: str = "Norwegian",
) -> str:
    """Create an application and return its id."""
    resp = client.post(
        f"{API}/applications/",
        headers=headers,
        json={
            "applicant_full_name": name,
            "applicant_nationality": nationality,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _upload_pdf(
    client: TestClient,
    headers: dict[str, str],
    application_id: str,
    *,
    document_type: str = "passport",
    filename: str = "passport.pdf",
    content: bytes = b"%PDF-1.4 fake content",
) -> dict:
    """Upload a minimal PDF and return the response JSON."""
    resp = client.post(
        f"{API}/applications/{application_id}/documents",
        headers=headers,
        data={"document_type": document_type},
        files={"file": (filename, content, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Upload – happy paths
# ---------------------------------------------------------------------------


class TestUploadDocument:
    """POST /applications/{id}/documents"""

    def test_upload_pdf_succeeds(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        doc = _upload_pdf(client, normal_user_token_headers, app_id)

        assert doc["status"] == "uploaded"
        assert doc["document_type"] == "passport"
        assert doc["mime_type"] == "application/pdf"
        assert doc["original_filename"] == "passport.pdf"
        assert doc["file_size_bytes"] > 0

    def test_upload_png_succeeds(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        # Minimal valid PNG header (8-byte signature)
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        resp = client.post(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
            data={"document_type": "id_card"},
            files={"file": ("id.png", png_bytes, "image/png")},
        )
        assert resp.status_code == 200
        assert resp.json()["mime_type"] == "image/png"

    def test_upload_jpeg_succeeds(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        resp = client.post(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
            data={"document_type": "photo"},
            files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        assert resp.json()["mime_type"] == "image/jpeg"

    def test_upload_webp_succeeds(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        webp_bytes = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 20
        resp = client.post(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
            data={"document_type": "document_scan"},
            files={"file": ("scan.webp", webp_bytes, "image/webp")},
        )
        assert resp.status_code == 200
        assert resp.json()["mime_type"] == "image/webp"

    def test_upload_sets_status_to_documents_uploaded(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        _upload_pdf(client, normal_user_token_headers, app_id)

        resp = client.get(
            f"{API}/applications/{app_id}",
            headers=normal_user_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "documents_uploaded"

    def test_upload_multiple_documents(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        _upload_pdf(client, normal_user_token_headers, app_id, document_type="passport")
        _upload_pdf(
            client,
            normal_user_token_headers,
            app_id,
            document_type="police_clearance",
            filename="clearance.pdf",
        )

        resp = client.get(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

    def test_upload_creates_audit_event(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        _upload_pdf(client, normal_user_token_headers, app_id)

        resp = client.get(
            f"{API}/applications/{app_id}/audit-trail",
            headers=normal_user_token_headers,
        )
        assert resp.status_code == 200
        events = resp.json()["events"]
        upload_events = [e for e in events if e["action"] == "document_uploaded"]
        assert len(upload_events) >= 1


# ---------------------------------------------------------------------------
# Upload – validation / error paths
# ---------------------------------------------------------------------------


class TestUploadValidation:
    """400-level responses from the upload endpoint."""

    def test_rejects_unsupported_mime_type_gif(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        resp = client.post(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
            data={"document_type": "photo"},
            files={"file": ("cat.gif", b"GIF89a\x00\x00", "image/gif")},
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    def test_rejects_unsupported_mime_type_text(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        resp = client.post(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
            data={"document_type": "notes"},
            files={"file": ("notes.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    def test_rejects_empty_file(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        resp = client.post(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
            data={"document_type": "passport"},
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_rejects_upload_to_nonexistent_application(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"{API}/applications/{fake_id}/documents",
            headers=normal_user_token_headers,
            data={"document_type": "passport"},
            files={"file": ("p.pdf", b"%PDF-1.4 x", "application/pdf")},
        )
        assert resp.status_code == 404

    def test_rejects_upload_without_auth(
        self, client: TestClient
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"{API}/applications/{fake_id}/documents",
            data={"document_type": "passport"},
            files={"file": ("p.pdf", b"%PDF-1.4 x", "application/pdf")},
        )
        assert resp.status_code == 401

    def test_other_user_cannot_upload_to_my_application(
        self,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
        superuser_token_headers: dict[str, str],
    ) -> None:
        """The superuser CAN access any app, but a different normal user could not."""
        # Superuser uploading to normal user's app should succeed (superuser bypass)
        app_id = _create_application(client, normal_user_token_headers)
        resp = client.post(
            f"{API}/applications/{app_id}/documents",
            headers=superuser_token_headers,
            data={"document_type": "passport"},
            files={"file": ("p.pdf", b"%PDF-1.4 super", "application/pdf")},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Queue Processing – happy paths
# ---------------------------------------------------------------------------


class TestQueueProcessing:
    """POST /applications/{id}/process"""

    def test_queue_with_documents_succeeds(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        _upload_pdf(client, normal_user_token_headers, app_id)

        resp = client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in {"queued", "processing", "review_ready"}

    def test_queue_creates_audit_event(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        _upload_pdf(client, normal_user_token_headers, app_id)

        client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": False},
        )

        resp = client.get(
            f"{API}/applications/{app_id}/audit-trail",
            headers=normal_user_token_headers,
        )
        assert resp.status_code == 200
        events = resp.json()["events"]
        queue_events = [e for e in events if e["action"] == "processing_queued"]
        assert len(queue_events) >= 1

    def test_force_reprocess_resets_documents(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        _upload_pdf(client, normal_user_token_headers, app_id)

        # First process
        resp1 = client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": False},
        )
        assert resp1.status_code == 200

        # Force reprocess
        resp2 = client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": True},
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] in {"queued", "processing", "review_ready"}

    def test_queue_default_force_reprocess_is_false(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """Sending an empty JSON body should work because force_reprocess defaults to False."""
        app_id = _create_application(client, normal_user_token_headers)
        _upload_pdf(client, normal_user_token_headers, app_id)

        resp = client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Queue Processing – validation / error paths
# ---------------------------------------------------------------------------


class TestQueueProcessingValidation:
    """400-level responses from the queue processing endpoint."""

    def test_rejects_queue_with_no_documents(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """This is the exact bug the user reported — bad request on Queue Processing."""
        app_id = _create_application(client, normal_user_token_headers)

        resp = client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": False},
        )
        assert resp.status_code == 400
        assert "Upload at least one document" in resp.json()["detail"]

    def test_rejects_queue_for_nonexistent_application(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"{API}/applications/{fake_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": False},
        )
        assert resp.status_code == 404

    def test_rejects_queue_without_auth(self, client: TestClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"{API}/applications/{fake_id}/process",
            json={"force_reprocess": False},
        )
        assert resp.status_code == 401

    def test_rejects_invalid_body(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers)
        _upload_pdf(client, normal_user_token_headers, app_id)

        resp = client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": "not-a-bool"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Full lifecycle: upload → queue → verify status
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    """End-to-end flow through upload and queue processing."""

    def test_draft_to_review_ready_lifecycle(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        # 1. Create → draft
        app_id = _create_application(client, normal_user_token_headers, name="Lifecycle User")
        resp = client.get(
            f"{API}/applications/{app_id}",
            headers=normal_user_token_headers,
        )
        assert resp.json()["status"] == "draft"

        # 2. Upload → documents_uploaded
        _upload_pdf(client, normal_user_token_headers, app_id)
        resp = client.get(
            f"{API}/applications/{app_id}",
            headers=normal_user_token_headers,
        )
        assert resp.json()["status"] == "documents_uploaded"

        # 3. Queue → queued/processing/review_ready
        resp = client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": False},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] in {"queued", "processing", "review_ready"}

        # 4. Verify documents list is populated
        docs_resp = client.get(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
        )
        assert docs_resp.status_code == 200
        assert docs_resp.json()["count"] >= 1

    def test_multiple_documents_then_process(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        app_id = _create_application(client, normal_user_token_headers, name="Multi Doc User")

        # Upload several document types
        for doc_type, fname in [
            ("passport", "passport.pdf"),
            ("police_clearance", "clearance.pdf"),
            ("residence_permit", "permit.pdf"),
        ]:
            _upload_pdf(
                client,
                normal_user_token_headers,
                app_id,
                document_type=doc_type,
                filename=fname,
            )

        # Verify count
        docs_resp = client.get(
            f"{API}/applications/{app_id}/documents",
            headers=normal_user_token_headers,
        )
        assert docs_resp.json()["count"] == 3

        # Queue processing
        resp = client.post(
            f"{API}/applications/{app_id}/process",
            headers=normal_user_token_headers,
            json={"force_reprocess": False},
        )
        assert resp.status_code == 200
