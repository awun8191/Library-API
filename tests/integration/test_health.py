"""Integration tests for the health route."""
import pytest
from fastapi.testclient import TestClient

from modules.health import service as health_service


class BrokenSessionFactory:
    """A session factory that fails like an unreachable database."""

    def __call__(self):
        raise RuntimeError("the database is down")


class BrokenManager:
    """A database manager with a broken session factory."""

    session_factory = BrokenSessionFactory()


def test_health_reports_a_ready_application(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "database", "version"}
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"] == "v1"


def test_health_returns_503_when_the_database_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health_service, "get_db_manager", lambda: BrokenManager())

    response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "error"


def test_health_needs_no_token_and_sits_outside_the_api_prefix(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "www-authenticate" not in response.headers
    assert client.get("/api/v1/health").status_code == 404
