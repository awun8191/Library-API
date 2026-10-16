"""User resource API routes."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.config import AppSettings
from dependencies import get_current_user, get_db
from modules.departments.repository import SqlAlchemyDepartmentRepository
from modules.users.data import UserResponse, UserUpdateRequest
from modules.users.repository import SqlAlchemyUserRepository
from modules.users.service import UserService


def get_users_router(settings: AppSettings) -> APIRouter:
    """Return the user router."""
    router = APIRouter()

    @router.get(
        f"/api/{settings.api_version}/users/me",
        response_model=UserResponse,
        status_code=status.HTTP_200_OK,
        tags=["Users"],
        summary="Current user profile",
        responses={
            200: {"description": "Current user profile fetched successfully"},
            401: {"description": "Unauthenticated"},
            404: {"description": "User not found"},
        },
    )
    async def get_me(
        current_user: UserResponse = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        """Retrieve the profile of the currently authenticated user."""
        service = UserService(
            user_repo=SqlAlchemyUserRepository(db),
            dept_repo=SqlAlchemyDepartmentRepository(db),
        )
        return service.get_user_profile(current_user.id)

    @router.put(
        f"/api/{settings.api_version}/users/me",
        response_model=UserResponse,
        status_code=status.HTTP_200_OK,
        tags=["Users"],
        summary="Update own profile",
        responses={
            200: {"description": "Profile updated successfully"},
            400: {"description": "Bad request"},
            401: {"description": "Unauthenticated"},
            404: {"description": "User or department not found"},
        },
    )
    async def update_me(
        payload: UserUpdateRequest,
        current_user: UserResponse = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        """Update fields on the current user's profile."""
        service = UserService(
            user_repo=SqlAlchemyUserRepository(db),
            dept_repo=SqlAlchemyDepartmentRepository(db),
        )
        return service.update_user_profile(current_user.id, payload)

    return router
