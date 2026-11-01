"""Unit tests for the authentication use cases."""
from typing import Optional

import pytest

from core.exceptions import (
    DepartmentNotFoundException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserForbiddenException,
)
from integrations.security import Argon2PasswordHasher, JwtTokenIssuer
from modules.auth.data import LoginRequest, SignupRequest
from modules.auth.service import AuthService
from tests.fakes import FakeAuthRepository, FakeDepartmentRepository

SECRET_KEY = "unit-test-secret-key-for-library-api-0001"


def build_issuer() -> JwtTokenIssuer:
    """Build a token issuer for the tests."""
    return JwtTokenIssuer(secret_key=SECRET_KEY, algorithm="HS256", expire_minutes=60)


def build_service(
    repository: FakeAuthRepository,
    dept_repo: Optional[FakeDepartmentRepository] = None,
    issuer: Optional[JwtTokenIssuer] = None,
) -> AuthService:
    """Build the authentication service on top of the fakes."""
    return AuthService(
        repository=repository,
        hasher=Argon2PasswordHasher(),
        token_issuer=issuer or build_issuer(),
        dept_repo=dept_repo,
    )


def build_signup(
    email: str = "ada@school.edu",
    password: str = "strong-password",
    department_id: Optional[int] = None,
) -> SignupRequest:
    """Build a valid signup request."""
    return SignupRequest(
        first_name="Ada",
        last_name="Obi",
        email=email,
        password=password,
        department_id=department_id,
    )


def test_signup_stores_a_hash_and_returns_a_plain_user():
    repository = FakeAuthRepository()
    service = build_service(repository)

    created = service.signup(build_signup())

    assert created.role == "user"
    assert created.is_active is True
    stored = repository.get_credentials_by_email("ada@school.edu")
    assert stored is not None
    assert stored.password_hash != "strong-password"
    assert Argon2PasswordHasher().verify("strong-password", stored.password_hash) is True


def test_signup_with_a_duplicate_email_raises():
    repository = FakeAuthRepository()
    repository.add_user(email="ada@school.edu", password_hash="existing-hash")
    service = build_service(repository)

    with pytest.raises(UserAlreadyExistsException):
        service.signup(build_signup())

    assert repository.created == []


def test_signup_with_an_unknown_department_raises():
    repository = FakeAuthRepository()
    dept_repo = FakeDepartmentRepository()
    service = build_service(repository, dept_repo=dept_repo)

    with pytest.raises(DepartmentNotFoundException):
        service.signup(build_signup(department_id=99))

    assert repository.created == []


def test_login_returns_a_token_for_the_user():
    repository = FakeAuthRepository()
    user = repository.add_user(
        email="ada@school.edu",
        password_hash=Argon2PasswordHasher().hash("strong-password"),
    )
    issuer = build_issuer()
    service = build_service(repository, issuer=issuer)

    token_response = service.login(
        LoginRequest(email="ada@school.edu", password="strong-password")
    )

    assert token_response.token_type == "bearer"
    assert token_response.expires_in == 3600
    assert issuer.decode_user_id(token_response.access_token) == user.id


def test_login_with_a_wrong_password_raises():
    repository = FakeAuthRepository()
    repository.add_user(
        email="ada@school.edu",
        password_hash=Argon2PasswordHasher().hash("strong-password"),
    )
    service = build_service(repository)

    with pytest.raises(InvalidCredentialsException):
        service.login(LoginRequest(email="ada@school.edu", password="wrong-password"))


def test_login_with_an_unknown_email_raises():
    repository = FakeAuthRepository()
    service = build_service(repository)

    with pytest.raises(InvalidCredentialsException):
        service.login(LoginRequest(email="nobody@school.edu", password="strong-password"))


def test_login_on_an_inactive_account_raises():
    repository = FakeAuthRepository()
    repository.add_user(
        email="ada@school.edu",
        password_hash=Argon2PasswordHasher().hash("strong-password"),
        is_active=False,
    )
    service = build_service(repository)

    with pytest.raises(UserForbiddenException):
        service.login(LoginRequest(email="ada@school.edu", password="strong-password"))
