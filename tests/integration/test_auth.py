"""Integration tests for the signup and login endpoints."""
import uuid

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from integrations.security import JwtTokenIssuer
from schema.models import User
from tests.conftest import DEFAULT_PASSWORD, TEST_SECRET_KEY

SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/users/me"

PUBLIC_USER_FIELDS = {
    "id",
    "first_name",
    "last_name",
    "email",
    "role",
    "is_active",
    "department_id",
}

NEW_PASSWORD = "strong-password"


def signup_payload(**overrides) -> dict:
    """Build a valid signup body. Each call uses a fresh email."""
    payload = {
        "first_name": "Ada",
        "last_name": "Obi",
        "email": f"student-{uuid.uuid4().hex[:10]}@school.edu",
        "password": NEW_PASSWORD,
    }
    payload.update(overrides)
    return payload


def test_signup_returns_201_with_public_fields_only(
    client: TestClient, make_department
) -> None:
    department = make_department(name="Computer Science")

    response = client.post(SIGNUP_URL, json=signup_payload(department_id=department.id))

    assert response.status_code == 201
    body = response.json()
    assert set(body) == PUBLIC_USER_FIELDS
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Obi"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert body["department_id"] == department.id
    assert "password_hash" not in body


def test_signup_with_a_duplicate_email_returns_409(
    client: TestClient, make_user
) -> None:
    make_user(email="ada@school.edu")

    response = client.post(SIGNUP_URL, json=signup_payload(email="ada@school.edu"))

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "USER_ALREADY_EXISTS"
    assert body["message"] == "An account with this email already exists"


def test_signup_with_a_short_password_returns_400_with_errors(
    client: TestClient,
) -> None:
    response = client.post(SIGNUP_URL, json=signup_payload(password="short12"))

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_REQUEST"
    assert body["message"] == "Invalid request data"
    assert [error["field"] for error in body["errors"]] == ["password"]


def test_signup_with_a_malformed_email_returns_400(client: TestClient) -> None:
    response = client.post(SIGNUP_URL, json=signup_payload(email="not-an-email"))

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_REQUEST"
    assert [error["field"] for error in body["errors"]] == ["email"]


def test_signup_with_an_unknown_department_returns_404(client: TestClient) -> None:
    response = client.post(SIGNUP_URL, json=signup_payload(department_id=987654))

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "DEPARTMENT_NOT_FOUND"
    assert body["message"] == "Department not found"


def test_signup_stores_an_argon2_hash_not_the_password(
    client: TestClient, db_session
) -> None:
    payload = signup_payload(email="hash-check@school.edu")

    response = client.post(SIGNUP_URL, json=payload)

    assert response.status_code == 201
    db_session.expire_all()
    user = db_session.execute(
        select(User).where(User.email == "hash-check@school.edu")
    ).scalar_one()
    assert user.password_hash != payload["password"]
    assert payload["password"] not in user.password_hash
    assert user.password_hash.startswith("$argon2id$")


def test_login_returns_a_token_response(client: TestClient, make_user) -> None:
    make_user(email="login@school.edu", password=DEFAULT_PASSWORD)

    response = client.post(
        LOGIN_URL, json={"email": "login@school.edu", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_in"}
    assert isinstance(body["access_token"], str)
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600


def test_login_with_a_wrong_password_returns_401(
    client: TestClient, make_user
) -> None:
    make_user(email="login@school.edu", password=DEFAULT_PASSWORD)

    response = client.post(
        LOGIN_URL, json={"email": "login@school.edu", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    body = response.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Invalid email or password"


def test_login_with_an_unknown_email_returns_the_same_401(
    client: TestClient, make_user
) -> None:
    make_user(email="known@school.edu", password=DEFAULT_PASSWORD)

    response = client.post(
        LOGIN_URL, json={"email": "unknown@school.edu", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    body = response.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Invalid email or password"


def test_login_on_an_inactive_account_returns_403(
    client: TestClient, make_user
) -> None:
    make_user(email="inactive@school.edu", password=DEFAULT_PASSWORD, is_active=False)

    response = client.post(
        LOGIN_URL, json={"email": "inactive@school.edu", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "FORBIDDEN"
    assert body["message"] == "This account is inactive"


def test_login_token_reads_the_profile(client: TestClient, make_user) -> None:
    user = make_user(email="token@school.edu", password=DEFAULT_PASSWORD)
    login = client.post(
        LOGIN_URL, json={"email": "token@school.edu", "password": DEFAULT_PASSWORD}
    )
    token = login.json()["access_token"]

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["id"] == user.id


def test_token_signed_with_another_key_returns_401(
    client: TestClient, make_user
) -> None:
    user = make_user()
    other_issuer = JwtTokenIssuer(
        secret_key="another-secret-key-that-the-api-does-not-know-0001",
        algorithm="HS256",
        expire_minutes=60,
    )
    token, _ = other_issuer.issue(user.id)

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    body = response.json()
    assert body["code"] == "UNAUTHENTICATED"
    assert jwt.decode(token, options={"verify_signature": False})["sub"] == str(user.id)
    assert TEST_SECRET_KEY != other_issuer.secret_key
