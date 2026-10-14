"""Application dependency wiring shared across resource modules."""
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import AppSettings, get_settings
from core.exceptions import UserForbiddenException, UserNotAuthorizedException
from modules.users.data import UserResponse

security = HTTPBearer(auto_error=False)


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
        role="user",
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
