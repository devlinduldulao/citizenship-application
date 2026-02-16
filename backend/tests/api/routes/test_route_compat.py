from fastapi.testclient import TestClient

from app.core.config import settings


def test_root_endpoint_exists(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    payload = r.json()
    assert payload["docs"] == "/docs"
    assert payload["redoc"] == "/redoc"
    assert payload["openapi"] == f"{settings.API_V1_STR}/openapi.json"


def test_healthz_endpoint_exists(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_root_compat_redirect(client: TestClient) -> None:
    r = client.get("/openapi.json", follow_redirects=False)
    assert r.status_code in {307, 308}
    assert r.headers["location"] == f"{settings.API_V1_STR}/openapi.json"


def test_api_v1_docs_compat_redirect(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/docs", follow_redirects=False)
    assert r.status_code in {307, 308}
    assert r.headers["location"] == "/docs"


def test_api_v1_redoc_compat_redirect(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/redoc", follow_redirects=False)
    assert r.status_code in {307, 308}
    assert r.headers["location"] == "/redoc"
