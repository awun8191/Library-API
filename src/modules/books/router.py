"""Book resource API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from core.config import AppSettings
from dependencies import get_current_user, get_db, require_admin
from integrations.file_storage import FileStorage
from modules.books.data import (
    BookAccessHistoryResponse,
    BookAccessResponse,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)
from modules.books.repository import SqlAlchemyBookRepository
from modules.books.service import BookService
from modules.departments.repository import SqlAlchemyDepartmentRepository
from modules.users.data import UserResponse


def get_book_service(db: Session = Depends(get_db)) -> BookService:
    """Dependency that instantiates BookService with its repository and storage adapters."""
    return BookService(
        book_repo=SqlAlchemyBookRepository(db),
        file_storage=FileStorage(),
        dept_repo=SqlAlchemyDepartmentRepository(db),
    )


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
            404: {"description": "Department not found"},
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
        service: BookService = Depends(get_book_service),
    ):
        """Upload a course material PDF (Admin only)."""
        return await service.upload_book(
            name=name,
            course_name=course_name,
            topic=topic,
            course_code=course_code,
            department_id=department_id,
            file=file,
            uploaded_by=current_admin.id,
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
        },
    )
    async def list_books(
        q: Optional[str] = Query(default=None, description="Search term for book name"),
        department_id: Optional[int] = Query(default=None, description="Filter by department ID"),
        cursor: Optional[int] = Query(default=None, description="Cursor pagination offset/ID"),
        limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
        service: BookService = Depends(get_book_service),
    ):
        """List books matching search criteria and department filters with cursor-based pagination."""
        return service.list_books(
            q=q,
            department_id=department_id,
            cursor=cursor,
            limit=limit,
        )

    @router.get(
        f"/api/{settings.api_version}/books/{{id}}",
        response_model=BookResponse,
        status_code=status.HTTP_200_OK,
        tags=["Books"],
        summary="Get details of a single book",
        responses={
            200: {"description": "Book details fetched successfully"},
            404: {"description": "Book not found"},
        },
    )
    async def get_book(
        id: int,
        service: BookService = Depends(get_book_service),
    ):
        """Retrieve details of a single course material by ID."""
        return service.get_book(id)

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
            404: {"description": "Book or department not found"},
        },
    )
    async def update_book(
        id: int,
        payload: BookUpdateRequest,
        current_admin: UserResponse = Depends(require_admin),
        service: BookService = Depends(get_book_service),
    ):
        """Update book metadata (Admin only)."""
        return service.update_book(id, payload)

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
        service: BookService = Depends(get_book_service),
    ):
        """Delete a book and its stored file (Admin only)."""
        service.delete_book(id)
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
        service: BookService = Depends(get_book_service),
    ):
        """Record that the current user opened a book."""
        return service.record_access(book_id=id, user_id=current_user.id)

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
        service: BookService = Depends(get_book_service),
    ):
        """Retrieve the reading/access history for the current user with cursor pagination."""
        return service.get_user_access_history(
            user_id=current_user.id,
            cursor=cursor,
            limit=limit,
        )

    return router
