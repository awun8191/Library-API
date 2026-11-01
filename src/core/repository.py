"""Contracts for the infrastructure adapters used by the services."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Tuple


class FileStorageRepository(Protocol):
    async def store_file(self, content: bytes) -> str:
        """Store the bytes of a PDF and return the stored path."""
        ...

    def get_file_path(self, file_path: str) -> str:
        """Return a readable path for streaming, or raise when the file is missing."""
        ...

    def delete_file(self, file_path: str) -> bool:
        """Delete a stored file and report whether it existed."""
        ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str:
        """Hash a plain password."""
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Check a plain password against a stored hash."""
        ...


class TokenIssuer(Protocol):
    def issue(self, user_id: int) -> Tuple[str, int]:
        """Issue an access token for a user and return it with its lifetime in seconds."""
        ...

    def decode_user_id(self, token: str) -> Optional[int]:
        """Return the user id in a valid token, or None when the token is invalid or expired."""
        ...


@dataclass(frozen=True)
class RateLimitHit:
    """Report one counter after an increment."""

    hits: int
    window_start: datetime
    window_seconds: int


class RateLimitStore(Protocol):
    def increment(self, key: str, window_seconds: int) -> RateLimitHit:
        """Add one hit to the counter of the key and return the new state."""
        ...

    def prune(self, older_than_seconds: int) -> None:
        """Delete the counters whose window started before the cutoff."""
        ...
