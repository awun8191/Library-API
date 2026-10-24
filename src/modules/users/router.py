"""User resource API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from core.config import AppSettings
from dependencies import get_book_service, get_current_user, get_user_service
from modules.books.data import BookAccessHistoryResponse
from modules.books.service import BookService
from modules.users.data import UserResponse, UserUpdateRequest
from modules.users.service import UserService


def get_users_router(settings: AppSettings) -> APIRouter:
    """Return the user router."""
    router = APIRouter(prefix=settings.api_prefix)

    @router.get(
        "/users/me",
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
    def get_me(current_user: UserResponse = Depends(get_current_user)):
        """Retrieve the profile of the currently authenticated user.

        get_current_user already reads the user from the database on this request.
        """
        return current_user

    @router.patch(
        "/users/me",
        response_model=UserResponse,
        status_code=status.HTTP_200_OK,
        tags=["Users"],
        summary="Update own profile",
        responses={
            200: {"description": "Profile updated successfully"},
            400: {"description": "Invalid request data"},
            401: {"description": "Unauthenticated"},
            404: {"description": "User or department not found"},
        },
    )
    def update_me(
        payload: UserUpdateRequest,
        current_user: UserResponse = Depends(get_current_user),
        service: UserService = Depends(get_user_service),
    ):
        """Update fields on the current user's profile."""
        return service.update_user_profile(current_user.id, payload)

    @router.get(
        "/users/me/access-history",
        response_model=BookAccessHistoryResponse,
        status_code=status.HTTP_200_OK,
        tags=["Users"],
        summary="Books the current user has opened",
        responses={
            200: {"description": "Access history fetched successfully"},
            400: {"description": "Invalid request data"},
            401: {"description": "Unauthenticated"},
        },
    )
    def get_my_access_history(
        cursor: Optional[int] = Query(default=None, description="Cursor from the previous page"),
        limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
        current_user: UserResponse = Depends(get_current_user),
        service: BookService = Depends(get_book_service),
    ):
        """Retrieve the reading history of the current user with cursor pagination."""
        return service.get_user_access_history(
            user_id=current_user.id,
            cursor=cursor,
            limit=limit,
        )

    return router
