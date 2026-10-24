"""Book resource API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from core.config import AppSettings
from dependencies import get_book_service, get_current_user, require_admin
from modules.books.data import (
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)
from modules.books.service import BookService
from modules.users.data import UserResponse


def _download_filename(name: str) -> str:
    """Build a safe file name for the Content-Disposition header."""
    safe = "".join(char if char.isalnum() or char in " -_" else "_" for char in name).strip()
    return f"{safe or 'book'}.pdf"


def get_books_router(settings: AppSettings) -> APIRouter:
    """Return the books router."""
    router = APIRouter(prefix=settings.api_prefix)

    @router.post(
        "/books",
        response_model=BookResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Books"],
        summary="Upload a book (PDF)",
        responses={
            201: {"description": "Book uploaded successfully"},
            400: {"description": "Invalid request data or invalid file type"},
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
        "/books",
        response_model=BookListResponse,
        status_code=status.HTTP_200_OK,
        tags=["Books"],
        summary="List books with search, filters, and cursor pagination",
        responses={
            200: {"description": "Books fetched successfully"},
            400: {"description": "Invalid request data"},
        },
    )
    def list_books(
        q: Optional[str] = Query(default=None, description="Search term for book name"),
        department_id: Optional[int] = Query(default=None, description="Filter by department ID"),
        course_code: Optional[str] = Query(default=None, description="Filter by course code"),
        cursor: Optional[int] = Query(default=None, description="Cursor from the previous page"),
        limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
        service: BookService = Depends(get_book_service),
    ):
        """List books that match the search term and the filters."""
        return service.list_books(
            q=q,
            department_id=department_id,
            course_code=course_code,
            cursor=cursor,
            limit=limit,
        )

    @router.get(
        "/books/{id}",
        response_model=BookResponse,
        status_code=status.HTTP_200_OK,
        tags=["Books"],
        summary="Get details of a single book",
        responses={
            200: {"description": "Book details fetched successfully"},
            404: {"description": "Book not found"},
        },
    )
    def get_book(
        id: int,
        service: BookService = Depends(get_book_service),
    ):
        """Retrieve details of a single course material by ID."""
        return service.get_book(id)

    @router.get(
        "/books/{id}/file",
        status_code=status.HTTP_200_OK,
        tags=["Books"],
        summary="Download a book PDF",
        responses={
            200: {"description": "PDF stream"},
            401: {"description": "Unauthenticated"},
            403: {"description": "Account is inactive"},
            404: {"description": "Book or stored file not found"},
        },
    )
    def download_book(
        id: int,
        current_user: UserResponse = Depends(get_current_user),
        service: BookService = Depends(get_book_service),
    ):
        """Stream the stored PDF and record the access for the current user."""
        file_path, book = service.open_book(book_id=id, user_id=current_user.id)
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=_download_filename(book.name),
            content_disposition_type="inline",
            headers={"Cache-Control": "private, no-store"},
        )

    @router.patch(
        "/books/{id}",
        response_model=BookResponse,
        status_code=status.HTTP_200_OK,
        tags=["Books"],
        summary="Update a book (Admin only)",
        responses={
            200: {"description": "Book updated successfully"},
            400: {"description": "Invalid request data"},
            401: {"description": "Unauthenticated"},
            403: {"description": "Forbidden (Admin only)"},
            404: {"description": "Book or department not found"},
        },
    )
    def update_book(
        id: int,
        payload: BookUpdateRequest,
        current_admin: UserResponse = Depends(require_admin),
        service: BookService = Depends(get_book_service),
    ):
        """Update book metadata (Admin only)."""
        return service.update_book(id, payload)

    @router.delete(
        "/books/{id}",
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
    def delete_book(
        id: int,
        current_admin: UserResponse = Depends(require_admin),
        service: BookService = Depends(get_book_service),
    ):
        """Delete a book and its stored file (Admin only)."""
        service.delete_book(id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
