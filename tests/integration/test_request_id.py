"""Integration tests for the request identifier middleware."""

import re
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.config import get_settings
from dependencies import get_db
from main import app

BOOKS_URL = "/api/v1/books"
GENERATED_ID = re.compile(r"^[0-9a-f]{32}$")


@pytest.fixture
def failing_client(db_session: Session) -> Generator[TestClient]:
    """Build a client that returns the 500 response instead of raising it."""

    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


def test_a_normal_response_carries_a_generated_id(client: TestClient) -> None:
    response = client.get("/api/v1/departments")

    assert response.status_code == 200
    assert GENERATED_ID.fullmatch(response.headers["X-Request-ID"])


def test_a_valid_incoming_id_is_echoed(client: TestClient) -> None:
    response = client.get("/api/v1/departments", headers={"X-Request-ID": "client.abc_123-XYZ"})

    assert response.headers["X-Request-ID"] == "client.abc_123-XYZ"


def test_an_invalid_incoming_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/v1/departments", headers={"X-Request-ID": "has space and!"})

    assert response.headers["X-Request-ID"] != "has space and!"
    assert GENERATED_ID.fullmatch(response.headers["X-Request-ID"])


def test_a_404_carries_the_id(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert GENERATED_ID.fullmatch(response.headers["X-Request-ID"])


def test_a_429_carries_the_id(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, rate_limit_store
) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_DEFAULT_PER_MINUTE", "1")
    get_settings.cache_clear()
    assert client.get(BOOKS_URL).status_code == 200

    response = client.get(BOOKS_URL)

    assert response.status_code == 429
    assert GENERATED_ID.fullmatch(response.headers["X-Request-ID"])


def test_a_500_keeps_the_id_in_the_body_and_the_header(
    failing_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    response = failing_client.get(
        BOOKS_URL, params={"q": "\x00"}, headers={"X-Request-ID": "trace-this-request"}
    )

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["request_id"] == response.headers["X-Request-ID"] == "trace-this-request"

    record = [item for item in caplog.records if item.name == "core.exceptions"][-1]
    assert record.levelname == "ERROR"
    assert record.exc_info is not None
    assert record.request_id == "trace-this-request"
