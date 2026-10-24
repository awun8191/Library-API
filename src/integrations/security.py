"""Password hashing and access token adapters."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2PasswordHasher:
    """Hash passwords with Argon2id."""

    def __init__(self) -> None:
        self._hasher = Argon2Hasher()
        # Checked when an email is unknown, so a failed login takes the same
        # time whether or not the account exists.
        self._dummy_hash = self._hasher.hash("timing-equaliser-password")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def dummy_verify(self, password: str) -> None:
        """Spend the same time as a real check, for unknown emails."""
        self.verify(password, self._dummy_hash)


TOKEN_ISSUER = "library-api"


class JwtTokenIssuer:
    """Issue and read signed JSON Web Tokens."""

    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 60) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def issue(self, user_id: int) -> Tuple[str, int]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.expire_minutes)
        payload = {"sub": str(user_id), "iat": now, "exp": expires_at, "iss": TOKEN_ISSUER}
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, self.expire_minutes * 60

    def decode_user_id(self, token: str) -> Optional[int]:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=TOKEN_ISSUER,
                options={"require": ["exp", "sub", "iss"]},
            )
        except jwt.InvalidTokenError:
            return None

        try:
            return int(payload["sub"])
        except (KeyError, TypeError, ValueError):
            return None
