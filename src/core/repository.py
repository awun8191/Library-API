"""Contracts for the infrastructure adapters used by the services."""
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
