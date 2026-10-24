"""Book resource persistence contracts and queries."""
from typing import Optional, Protocol, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.books.data import (
    BookAccessHistoryResponse,
    BookAccessItemResponse,
    BookAccessResponse,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
    normalize_course_code,
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

    def read_book_with_file(self, book_id: int) -> Optional[Tuple[BookResponse, str]]:
        """Fetch a book and its stored file name in one query."""
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

    def read_book_with_file(self, book_id: int) -> Optional[Tuple[BookResponse, str]]:
        stmt = select(Book).where(Book.id == book_id)
        book = self.session.execute(stmt).scalar_one_or_none()
        if not book:
            return None
        return BookResponse.model_validate(book), book.file_path

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

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(book, field, value)

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
            stmt = stmt.where(Book.course_code == normalize_course_code(course_code))
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
