"""Application dependency wiring shared across resource modules."""
from typing import Generator, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.config import AppSettings, get_settings
from core.exceptions import UserForbiddenException, UserNotAuthorizedException
from integrations.database import get_db_manager
from modules.users.data import UserResponse

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a transactional database session per request."""
    manager = get_db_manager()
    yield from manager.get_session()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: AppSettings = Depends(get_settings),
) -> UserResponse:
    """Dependency that resolves the authenticated user from the bearer token."""
    if not credentials:
        raise UserNotAuthorizedException(message="Authentication token is missing")

    # TODO: Decode and verify JWT token via auth service once token issuing is fully wired.
    # Placeholder returning current user context.
    token = credentials.credentials
    if not token:
        raise UserNotAuthorizedException(message="Invalid token")

    return UserResponse(
        id=1,
        first_name="Test",
        last_name="User",
        email="user@school.edu",
        role="admin",
        is_active=True,
        department_id=1,
    )


async def require_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Dependency ensuring the user has an admin role."""
    if current_user.role != "admin":
        raise UserForbiddenException(message="Admin access required")
    return current_user
