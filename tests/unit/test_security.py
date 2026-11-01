"""Unit tests for the password hasher and the token issuer."""
from datetime import datetime, timedelta, timezone

import jwt

from integrations.security import Argon2PasswordHasher, JwtTokenIssuer

SECRET_KEY = "unit-test-secret-key-for-library-api-0001"
OTHER_SECRET_KEY = "another-unit-test-secret-key-for-library-api"
ALGORITHM = "HS256"


def build_issuer(secret_key: str = SECRET_KEY) -> JwtTokenIssuer:
    """Build a token issuer for the tests."""
    return JwtTokenIssuer(secret_key=secret_key, algorithm=ALGORITHM, expire_minutes=60)


def encode_token(payload: dict, secret_key: str = SECRET_KEY) -> str:
    """Sign a token payload directly, without the issuer."""
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def future_time() -> datetime:
    """Return a time in the future."""
    return datetime.now(timezone.utc) + timedelta(hours=1)


def test_password_hash_accepts_the_original_password():
    hasher = Argon2PasswordHasher()

    password_hash = hasher.hash("correct-horse-battery")

    assert password_hash != "correct-horse-battery"
    assert hasher.verify("correct-horse-battery", password_hash) is True


def test_password_hash_rejects_a_wrong_password():
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash("correct-horse-battery")

    assert hasher.verify("wrong-battery-staple", password_hash) is False


def test_password_hash_rejects_a_malformed_stored_hash():
    hasher = Argon2PasswordHasher()

    assert hasher.verify("correct-horse-battery", "not-an-argon2-hash") is False


def test_issued_token_returns_the_user_id():
    issuer = build_issuer()

    token, expires_in = issuer.issue(7)

    assert expires_in == 3600
    assert issuer.decode_user_id(token) == 7


def test_expired_token_is_rejected():
    issuer = build_issuer()
    now = datetime.now(timezone.utc)
    token = encode_token(
        {
            "sub": "7",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "iss": "library-api",
        }
    )

    assert issuer.decode_user_id(token) is None


def test_token_signed_with_another_key_is_rejected():
    issuer = build_issuer()
    token = encode_token({"sub": "7", "exp": future_time()}, secret_key=OTHER_SECRET_KEY)

    assert issuer.decode_user_id(token) is None


def test_token_without_a_subject_is_rejected():
    issuer = build_issuer()
    token = encode_token({"exp": future_time()})

    assert issuer.decode_user_id(token) is None


def test_token_with_a_non_numeric_subject_is_rejected():
    issuer = build_issuer()
    token = encode_token({"sub": "not-a-number", "exp": future_time()})

    assert issuer.decode_user_id(token) is None
