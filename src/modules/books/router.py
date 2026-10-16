"""Book resource API routes."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from core.config import AppSettings
from dependencies import get_current_user, require_admin
from modules.books.data import BookListResponse, BookResponse, BookUpdateRequest, BookAccessResponse, \
    BookAccessHistoryResponse
from modules.users.data import UserResponse


def get_books_router(settings: AppSettings) -> APIRouter:
    """Return the books router."""
    router = APIRouter()

    @router.post(
        f"/api/{settings.api_version}/books",
        response_model=BookResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Books"],
        summary="Upload a book (PDF)",
        responses={
            201: {"description": "Book uploaded successfully"},
            400: {"description": "Bad request (e.g. invalid file type)"},
            401: {"description": "Unauthenticated"},
            403: {"description": "Forbidden (Admin only)"},
            409: {"description": "Conflict (Duplicate file hash)"},
        },
    )
    async def upload_book(
        name: str = Form(...),
        course_name: str = Form(...),
        topic: str = Form(...),
        course_code: str = Form(...),
        department_id: int = Form(...),
        file: UploadFile = File(...),
        current_admin: UserResponse = Depends(require_admin),
    ):
        """Upload a course material PDF (Admin only)."""
        # Stub implementation pending service logic wiring
        return BookResponse(
            id=1,
            name=name,
            course_name=course_name,
            topic=topic,
            course_code=course_code,
            file_hash="dummy_hash_sha256",
            file_url=f"/static/books/{file.filename}",
            file_path=f"storage/books/{file.filename}",
            uploaded_by=current_admin.id,
            department_id=department_id,
        )

    @router.get(
        f"/api/{settings.api_version}/books",
        response_model=BookListResponse,
        status_code=status.HTTP_200_OK,
        tags=["Books"],
        summary="List books with search, department filter, and cursor pagination",
        responses={
            200: {"description": "Books fetched successfully"},
            400: {"description": "Bad request"},
            401: {"description": "Unauthenticated"},
        },
    )
    async def list_books(
        q: Optional[str] = Query(default=None, description="Search term for book name"),
        department_id: Optional[int] = Query(default=None, description="Filter by department ID"),
        cursor: Optional[int] = Query(default=None, description="Cursor pagination offset/ID"),
        limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
        current_user: UserResponse = Depends(get_current_user),
    ):
        """List books matching search criteria and department filters with cursor-based pagination."""
        return BookListResponse(
            items=[],
            next_cursor=None,
            has_more=False,
        )

    @router.get(
        f"/api/{settings.api_version}/books/{{id}}",
        response_model=BookResponse,
        status_code=status.HTTP_200_OK,
        tags=["Books"],
        summary="Get details of a single book",
        responses={
            200: {"description": "Book details fetched successfully"},
            401: {"description": "Unauthenticated"},
            404: {"description": "Book not found"},
        },
    )
    async def get_book(
        id: int,
        current_user: UserResponse = Depends(get_current_user),
    ):
        """Retrieve details of a single course material by ID."""
        return BookResponse(
            id=id,
            name="Sample Course Material",
            course_name="CS101",
            topic="Introduction to Programming",
            course_code="CS101",
            file_hash="sample_hash",
            file_url="/static/books/sample.pdf",
            file_path="storage/books/sample.pdf",
            uploaded_by=1,
            department_id=1,
        )

    @router.put(
        f"/api/{settings.api_version}/books/{{id}}",
        response_model=BookResponse,
        status_code=status.HTTP_200_OK,
        tags=["Books"],
        summary="Update a book (Admin only)",
        responses={
            200: {"description": "Book updated successfully"},
            400: {"description": "Bad request"},
            401: {"description": "Unauthenticated"},
            403: {"description": "Forbidden (Admin only)"},
            404: {"description": "Book not found"},
        },
    )
    async def update_book(
        id: int,
        payload: BookUpdateRequest,
        current_admin: UserResponse = Depends(require_admin),
    ):
        """Update book metadata (Admin only)."""
        return BookResponse(
            id=id,
            name=payload.name or "Updated Book Name",
            course_name=payload.course_name or "CS101",
            topic=payload.topic or "Topic",
            course_code=payload.course_code or "CS101",
            file_hash="sample_hash",
            file_url="/static/books/sample.pdf",
            file_path="storage/books/sample.pdf",
            uploaded_by=current_admin.id,
            department_id=payload.department_id or 1,
        )

    @router.delete(
        f"/api/{settings.api_version}/books/{{id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Books"],
        summary="Delete a book (Admin only)",
        responses={
            204: {"description": "Book deleted successfully"},
            401: {"description": "Unauthenticated"},
            403: {"description": "Forbidden (Admin only)"},
            404: {"description": "Book not found"},
        },
    )
    async def delete_book(
        id: int,
        current_admin: UserResponse = Depends(require_admin),
    ):
        """Delete a book and its stored file (Admin only)."""
        return Response(status_code=status.HTTP_204_NO_CONTENT)




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
