from fastapi.testclient import TestClient


def test_health_check_reports_database_status(client: TestClient) -> None:
    response = client.get("/api/v1/utils/health-check/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
