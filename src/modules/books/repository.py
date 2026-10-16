"""Book resource persistence contracts and queries."""
from typing import Optional, Protocol, runtime_checkable

from modules.books.data import (
    BookAccessHistoryResponse,
    BookAccessResponse,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)


@runtime_checkable
class BookRepository(Protocol):
    """Book repository interface defining persistence operations for books and access events."""

    def upload_book(
        self,
        name: str,
        course_name: str,
        topic: str,
        course_code: str,
        department_id: int,
        file_hash: str,
        file_url: str,
        file_path: str,
        uploaded_by: int,
    ) -> BookResponse:
        """Persist a new book record."""
        ...

    create_book = upload_book

    def read_book(self, book_id: int) -> Optional[BookResponse]:
        """Fetch a single book by ID."""
        ...

    def update_book(self, book_id: int, payload: BookUpdateRequest) -> Optional[BookResponse]:
        """Update an existing book record."""
        ...

    def delete_book(self, book_id: int) -> bool:
        """Delete a book record and return True if successful."""
        ...

    def list_books(
        self,
        q: Optional[str] = None,
        department_id: Optional[int] = None,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookListResponse:
        """List books with search query, department filter, and cursor-based pagination."""
        ...

    def record_access(self, book_id: int, user_id: int) -> BookAccessResponse:
        """Record an access/open event for a book by a user."""
        ...

    def get_user_access_history(
        self,
        user_id: int,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookAccessHistoryResponse:
        """Retrieve paginated reading history for a user."""
        ...



