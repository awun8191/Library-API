"""Integration tests for the rate limit middleware."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from core.config import get_settings
from integrations.rate_limit import PostgresRateLimitStore
from tests.conftest import DEFAULT_PASSWORD
from tests.integration.test_auth import signup_payload
from tests.integration.test_books import upload_book

LOGIN_URL = "/api/v1/auth/login"
SIGNUP_URL = "/api/v1/auth/signup"
BOOKS_URL = "/api/v1/books"


def configure_rate_limit(
    monkeypatch: pytest.MonkeyPatch, enabled: bool = True, **values: object
) -> None:
    """Turn the limiter on or off and apply the limits of one test."""
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true" if enabled else "false")
    for name, value in values.items():
        monkeypatch.setenv(name, str(value))
    get_settings.cache_clear()


def login(
    client: TestClient,
    email: str,
    password: str = DEFAULT_PASSWORD,
    headers: dict[str, str] | None = None,
):
    """Post one login request."""
    return client.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        headers=headers or {},
    )


def test_five_logins_in_a_minute_pass(
    client: TestClient, make_user, monkeypatch, rate_limit_store
) -> None:
    configure_rate_limit(monkeypatch)
    make_user(email="limit@school.edu", password=DEFAULT_PASSWORD)

    responses = [login(client, "limit@school.edu") for _ in range(5)]

    assert [response.status_code for response in responses] == [200] * 5


def test_the_sixth_login_in_a_minute_returns_429(
    client: TestClient, make_user, monkeypatch, rate_limit_store
) -> None:
    configure_rate_limit(monkeypatch)
    make_user(email="limit@school.edu", password=DEFAULT_PASSWORD)
    for _ in range(5):
        login(client, "limit@school.edu")

    response = login(client, "limit@school.edu", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"
    assert int(response.headers["Retry-After"]) >= 1
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert response.headers["X-RateLimit-Limit"] == "5"
    # CORS runs before the limiter, so a blocked browser request can read the body.
    assert response.headers["access-control-allow-origin"] == "*"


def test_the_rate_limited_body_holds_only_the_message_and_the_code(
    client: TestClient, make_user, monkeypatch, rate_limit_store
) -> None:
    configure_rate_limit(monkeypatch, RATE_LIMIT_LOGIN_PER_MINUTE="1")
    make_user(email="limit@school.edu", password=DEFAULT_PASSWORD)
    login(client, "limit@school.edu")

    response = login(client, "limit@school.edu")

    assert response.status_code == 429
    assert response.json() == {
        "message": "Too many requests. Try again later.",
        "code": "RATE_LIMITED",
    }


def test_two_real_ip_values_have_separate_counters(
    client: TestClient, make_user, monkeypatch, rate_limit_store
) -> None:
    configure_rate_limit(monkeypatch, TRUST_PROXY_HEADERS="true", RATE_LIMIT_LOGIN_PER_MINUTE="1")
    make_user(email="limit@school.edu", password=DEFAULT_PASSWORD)

    first = login(client, "limit@school.edu", headers={"X-Real-IP": "203.0.113.5"})
    second = login(client, "limit@school.edu", headers={"X-Real-IP": "203.0.113.9"})
    third = login(client, "limit@school.edu", headers={"X-Real-IP": "203.0.113.5"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_the_signup_limit_blocks_the_sixth_request(
    client: TestClient, monkeypatch, rate_limit_store
) -> None:
    configure_rate_limit(monkeypatch)

    responses = [client.post(SIGNUP_URL, json=signup_payload()) for _ in range(6)]

    assert [response.status_code for response in responses] == [201] * 5 + [429]


def test_the_upload_limit_applies_to_the_upload_route_only(
    client: TestClient,
    make_user,
    make_department,
    make_pdf,
    auth_headers,
    monkeypatch,
    rate_limit_store,
) -> None:
    configure_rate_limit(monkeypatch, RATE_LIMIT_UPLOAD_PER_HOUR="1")
    admin = make_user(role="admin")
    department = make_department()

    first = upload_book(client, auth_headers(admin), department.id, make_pdf("limit-1"))
    second = upload_book(client, auth_headers(admin), department.id, make_pdf("limit-2"))
    listing = client.get(BOOKS_URL)

    assert first.status_code == 201
    assert second.status_code == 429
    assert listing.status_code == 200


def test_a_lowered_default_limit_blocks_the_next_get(
    client: TestClient, monkeypatch, rate_limit_store
) -> None:
    configure_rate_limit(monkeypatch, RATE_LIMIT_DEFAULT_PER_MINUTE="2")

    first = client.get(BOOKS_URL)
    second = client.get(BOOKS_URL)
    third = client.get(BOOKS_URL)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_a_disabled_limiter_never_blocks(client: TestClient, monkeypatch, rate_limit_store) -> None:
    configure_rate_limit(monkeypatch, enabled=False, RATE_LIMIT_DEFAULT_PER_MINUTE="1")

    responses = [client.get(BOOKS_URL) for _ in range(4)]

    assert [response.status_code for response in responses] == [200] * 4
    assert rate_limit_store.counters == {}


def test_a_successful_response_carries_the_limit_headers(
    client: TestClient, monkeypatch, rate_limit_store
) -> None:
    configure_rate_limit(monkeypatch, RATE_LIMIT_DEFAULT_PER_MINUTE="3")

    response = client.get(BOOKS_URL)

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "3"
    assert response.headers["X-RateLimit-Remaining"] == "2"
    assert int(response.headers["X-RateLimit-Reset"]) >= 0


def test_a_new_window_allows_requests_again(
    client: TestClient, monkeypatch, rate_limit_store
) -> None:
    configure_rate_limit(monkeypatch, RATE_LIMIT_DEFAULT_PER_MINUTE="1")
    assert client.get(BOOKS_URL).status_code == 200
    assert client.get(BOOKS_URL).status_code == 429

    rate_limit_store.advance(61)
    response = client.get(BOOKS_URL)

    assert response.status_code == 200


@pytest.mark.postgres_store
def test_the_postgres_store_counts_and_prunes_in_the_test_database(db_engine) -> None:
    store = PostgresRateLimitStore(sessionmaker(bind=db_engine))
    key = f"pytest-counter-{uuid.uuid4().hex}"
    old_key = f"pytest-old-{uuid.uuid4().hex}"

    try:
        first = store.increment(key, 60)
        second = store.increment(key, 60)

        assert (first.hits, second.hits) == (1, 2)
        assert first.window_start == second.window_start
        assert second.window_seconds == 60

        with db_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO rate_limit_counters (key, window_start, hits) "
                    "VALUES (:key, now() - interval '2 days', 4)"
                ),
                {"key": old_key},
            )

        store.prune(86400)

        with db_engine.begin() as connection:
            stored = (
                connection.execute(
                    text("SELECT key FROM rate_limit_counters WHERE key IN (:key, :old_key)"),
                    {"key": key, "old_key": old_key},
                )
                .scalars()
                .all()
            )
        assert stored == [key]
    finally:
        with db_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM rate_limit_counters WHERE key IN (:key, :old_key)"),
                {"key": key, "old_key": old_key},
            )
