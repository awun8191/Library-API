"""Book-access history resource API routes."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from core.config import AppSettings
from dependencies import get_current_user
from modules.book_access.data import (
    BookAccessHistoryResponse,
    BookAccessResponse,
)
from modules.users.data import UserResponse


def get_book_access_router(settings: AppSettings) -> APIRouter:
    """Return the book-access history router."""
    router = APIRouter()

    @router.post(
        f"/api/{settings.api_version}/books/{{id}}/access",
        response_model=BookAccessResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Books", "Book Access"],
        summary="Record that the user opened the book",
        responses={
            201: {"description": "Book access event recorded successfully"},
            401: {"description": "Unauthenticated"},
            404: {"description": "Book not found"},
        },
    )
    async def record_book_access(
        id: int,
        current_user: UserResponse = Depends(get_current_user),
    ):
        """Record that the current user opened a book."""
        return BookAccessResponse(
            id=1,
            user_id=current_user.id,
            book_id=id,
            accessed_at=datetime.now(timezone.utc),
        )

    @router.get(
        f"/api/{settings.api_version}/users/me/access-history",
        response_model=BookAccessHistoryResponse,
        status_code=status.HTTP_200_OK,
        tags=["Users", "Book Access"],
        summary="Books the current user has opened — cursor-based pagination",
        responses={
            200: {"description": "Access history fetched successfully"},
            400: {"description": "Bad request"},
            401: {"description": "Unauthenticated"},
        },
    )
    async def get_user_access_history(
        cursor: Optional[int] = Query(default=None, description="Cursor pagination offset/ID"),
        limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
        current_user: UserResponse = Depends(get_current_user),
    ):
        """Retrieve the reading/access history for the current user with cursor pagination."""
        return BookAccessHistoryResponse(
            items=[],
            next_cursor=None,
            has_more=False,
        )

    return router