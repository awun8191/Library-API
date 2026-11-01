"""Integration tests for the current user profile endpoints."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from schema.models import User
from tests.conftest import TEST_SECRET_KEY

ME_URL = "/api/v1/users/me"


def test_get_me_returns_the_caller_profile(client: TestClient, make_user, auth_headers) -> None:
    user = make_user(first_name="Grace", last_name="Hopper", email="grace@school.edu")

    response = client.get(ME_URL, headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user.id
    assert body["first_name"] == "Grace"
    assert body["last_name"] == "Hopper"
    assert body["email"] == "grace@school.edu"
    assert "password_hash" not in body


def test_get_me_without_a_token_returns_401(client: TestClient) -> None:
    response = client.get(ME_URL)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    body = response.json()
    assert body["code"] == "UNAUTHENTICATED"
    assert body["message"] == "Authentication token is missing"


def test_get_me_with_an_expired_token_returns_401(client: TestClient, make_user) -> None:
    user = make_user()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "iss": "library-api",
        },
        TEST_SECRET_KEY,
        algorithm="HS256",
    )

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "UNAUTHENTICATED"
    assert body["message"] == "Invalid or expired authentication token"


def test_patch_me_updates_first_and_last_name(
    client: TestClient, make_user, auth_headers, db_session
) -> None:
    user = make_user(first_name="Ada", last_name="Obi")

    response = client.patch(
        ME_URL,
        json={"first_name": "Grace", "last_name": "Hopper"},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Grace"
    assert body["last_name"] == "Hopper"

    db_session.expire_all()
    row = db_session.execute(select(User).where(User.id == user.id)).scalar_one()
    assert row.first_name == "Grace"
    assert row.last_name == "Hopper"


def test_patch_me_with_an_unknown_department_returns_404(
    client: TestClient, make_user, auth_headers
) -> None:
    user = make_user()

    response = client.patch(ME_URL, json={"department_id": 987654}, headers=auth_headers(user))

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "DEPARTMENT_NOT_FOUND"
    assert body["message"] == "Department not found"


def test_patch_me_with_an_empty_body_changes_nothing(
    client: TestClient, make_user, auth_headers
) -> None:
    user = make_user(first_name="Ada", last_name="Obi")
    before = client.get(ME_URL, headers=auth_headers(user)).json()

    response = client.patch(ME_URL, json={}, headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == before


def test_patch_me_always_resolves_the_token_subject(
    client: TestClient, make_user, auth_headers, db_session
) -> None:
    caller = make_user(first_name="Ada", last_name="Obi")
    other = make_user(first_name="Grace", last_name="Hopper")

    response = client.patch(
        f"{ME_URL}?user_id={other.id}",
        json={"first_name": "Mallory"},
        headers=auth_headers(caller),
    )

    assert response.status_code == 200
    assert response.json()["id"] == caller.id
    assert response.json()["first_name"] == "Mallory"

    db_session.expire_all()
    rows = (
        db_session.execute(select(User).where(User.id.in_([caller.id, other.id])).order_by(User.id))
        .scalars()
        .all()
    )
    changed = {row.id: row.first_name for row in rows}
    assert changed[caller.id] == "Mallory"
    assert changed[other.id] == "Grace"
