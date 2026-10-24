"""Book resource persistence contracts and queries."""
from typing import Optional, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.books.data import (
    BookAccessHistoryResponse,
    BookAccessItemResponse,
    BookAccessResponse,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)
from schema.models import Book, BookAccess


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so a search term matches literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
        file_path: str,
        uploaded_by: int,
    ) -> BookResponse:
        """Persist a new book record."""
        ...

    def read_book(self, book_id: int) -> Optional[BookResponse]:
        """Fetch a single book by ID."""
        ...

    def read_file_path(self, book_id: int) -> Optional[str]:
        """Fetch the stored file path of a book."""
        ...

    def find_by_file_hash(self, file_hash: str) -> Optional[BookResponse]:
        """Fetch the book that already uses a file hash."""
        ...

    def update_book(self, book_id: int, payload: BookUpdateRequest) -> Optional[BookResponse]:
        """Update an existing book record."""
        ...

    def delete_book(self, book_id: int) -> Optional[str]:
        """Delete a book record and return its file_path if found, or None."""
        ...

    def list_books(
        self,
        q: Optional[str] = None,
        department_id: Optional[int] = None,
        course_code: Optional[str] = None,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookListResponse:
        """List books with search, filters, and cursor-based pagination."""
        ...

    def record_access(self, book_id: int, user_id: int) -> BookAccessResponse:
        """Record an access event for a book by a user."""
        ...

    def get_user_access_history(
        self,
        user_id: int,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookAccessHistoryResponse:
        """Retrieve paginated reading history for a user."""
        ...


class SqlAlchemyBookRepository:
    """SQLAlchemy implementation of the BookRepository contract."""

    def __init__(self, session: Session):
        self.session = session

    def upload_book(
        self,
        name: str,
        course_name: str,
        topic: str,
        course_code: str,
        department_id: int,
        file_hash: str,
        file_path: str,
        uploaded_by: int,
    ) -> BookResponse:
        book = Book(
            name=name,
            course_name=course_name,
            topic=topic,
            course_code=course_code,
            department_id=department_id,
            file_hash=file_hash,
            file_path=file_path,
            uploaded_by=uploaded_by,
        )
        self.session.add(book)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        self.session.refresh(book)
        return BookResponse.model_validate(book)

    def read_book(self, book_id: int) -> Optional[BookResponse]:
        stmt = select(Book).where(Book.id == book_id)
        book = self.session.execute(stmt).scalar_one_or_none()
        if not book:
            return None
        return BookResponse.model_validate(book)

    def read_file_path(self, book_id: int) -> Optional[str]:
        stmt = select(Book.file_path).where(Book.id == book_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def find_by_file_hash(self, file_hash: str) -> Optional[BookResponse]:
        stmt = select(Book).where(Book.file_hash == file_hash)
        book = self.session.execute(stmt).scalar_one_or_none()
        if not book:
            return None
        return BookResponse.model_validate(book)

    def update_book(self, book_id: int, payload: BookUpdateRequest) -> Optional[BookResponse]:
        stmt = select(Book).where(Book.id == book_id)
        book = self.session.execute(stmt).scalar_one_or_none()
        if not book:
            return None

        if payload.name is not None:
            book.name = payload.name
        if payload.course_name is not None:
            book.course_name = payload.course_name
        if payload.topic is not None:
            book.topic = payload.topic
        if payload.course_code is not None:
            book.course_code = payload.course_code
        if payload.department_id is not None:
            book.department_id = payload.department_id

        self.session.commit()
        self.session.refresh(book)
        return BookResponse.model_validate(book)

    def delete_book(self, book_id: int) -> Optional[str]:
        stmt = select(Book).where(Book.id == book_id)
        book = self.session.execute(stmt).scalar_one_or_none()
        if not book:
            return None

        file_path = book.file_path
        self.session.delete(book)
        self.session.commit()
        return file_path

    def list_books(
        self,
        q: Optional[str] = None,
        department_id: Optional[int] = None,
        course_code: Optional[str] = None,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookListResponse:
        stmt = select(Book)
        if q:
            stmt = stmt.where(Book.name.ilike(f"%{_escape_like(q)}%", escape="\\"))
        if department_id is not None:
            stmt = stmt.where(Book.department_id == department_id)
        if course_code:
            stmt = stmt.where(func.upper(Book.course_code) == course_code.strip().upper())
        if cursor is not None:
            stmt = stmt.where(Book.id > cursor)
        stmt = stmt.order_by(Book.id.asc()).limit(limit + 1)

        rows = self.session.execute(stmt).scalars().all()
        has_more = len(rows) > limit
        items_slice = rows[:limit]
        next_cursor = items_slice[-1].id if has_more and items_slice else None
        return BookListResponse(
            items=[BookResponse.model_validate(b) for b in items_slice],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def record_access(self, book_id: int, user_id: int) -> BookAccessResponse:
        access = BookAccess(
            user_id=user_id,
            book_id=book_id,
        )
        self.session.add(access)
        self.session.commit()
        self.session.refresh(access)
        return BookAccessResponse.model_validate(access)

    def get_user_access_history(
        self,
        user_id: int,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookAccessHistoryResponse:
        stmt = (
            select(
                BookAccess,
                Book.name.label("book_name"),
                Book.course_code.label("course_code"),
            )
            .join(Book, BookAccess.book_id == Book.id)
            .where(BookAccess.user_id == user_id)
        )
        if cursor is not None:
            stmt = stmt.where(BookAccess.id < cursor)
        stmt = stmt.order_by(BookAccess.id.desc()).limit(limit + 1)

        rows = self.session.execute(stmt).all()
        has_more = len(rows) > limit
        items_slice = rows[:limit]
        next_cursor = items_slice[-1][0].id if has_more and items_slice else None

        items = [
            BookAccessItemResponse(
                id=access.id,
                book_id=access.book_id,
                book_name=book_name,
                course_code=course_code,
                accessed_at=access.accessed_at,
            )
            for access, book_name, course_code in items_slice
        ]
        return BookAccessHistoryResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )
