"""User resource API routes."""
from fastapi import APIRouter, Depends, status

from core.config import AppSettings
from dependencies import get_current_user
from modules.users.data import UserResponse, UserUpdateRequest


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
        },
    )
    async def get_me(current_user: UserResponse = Depends(get_current_user)):
        """Retrieve the profile of the currently authenticated user."""
        return current_user

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
        },
    )
    async def update_me(
        payload: UserUpdateRequest,
        current_user: UserResponse = Depends(get_current_user),
    ):
        """Update fields on the current user's profile."""
        updated_data = current_user.model_dump()
        if payload.first_name is not None:
            updated_data["first_name"] = payload.first_name
        if payload.last_name is not None:
            updated_data["last_name"] = payload.last_name
        if payload.department_id is not None:
            updated_data["department_id"] = payload.department_id
        return UserResponse(**updated_data)

    return router
