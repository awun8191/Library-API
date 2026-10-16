"""Book resource business rules, queries, and use cases."""
import hashlib
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import (
    BookNotFoundException,
    DepartmentNotFoundException,
    DuplicateFileException,
)
from core.repository import FileStorageRepository
from modules.books.data import (
    BookAccessHistoryResponse,
    BookAccessItemResponse,
    BookAccessResponse,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)
from modules.departments.repository import DepartmentRepository
from schema.models import Book, BookAccess


class BookService:
    def __init__(
        self,
        db: Session,
        file_storage: FileStorageRepository,
        dept_repo: Optional[DepartmentRepository] = None,
    ):
        self.db = db
        self.file_storage = file_storage
        self.dept_repo = dept_repo

    async def upload_book(
        self,
        name: str,
        course_name: str,
        topic: str,
        course_code: str,
        department_id: int,
        file: UploadFile,
        uploaded_by: int,
    ) -> BookResponse:
        if self.dept_repo:
            dept = self.dept_repo.get_by_id(department_id)
            if not dept:
                raise DepartmentNotFoundException()

        content = await file.read()
        await file.seek(0)
        file_hash = hashlib.sha256(content).hexdigest()

        file_path, file_url = await self.file_storage.upload_file(file)

        book = Book(
            name=name,
            course_name=course_name,
            topic=topic,
            course_code=course_code,
            department_id=department_id,
            file_hash=file_hash,
            file_url=file_url,
            file_path=file_path,
            uploaded_by=uploaded_by,
        )
        self.db.add(book)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            self.file_storage.delete_file(file_path)
            raise DuplicateFileException() from exc
        except Exception:
            self.db.rollback()
            self.file_storage.delete_file(file_path)
            raise

        self.db.refresh(book)
        return BookResponse.model_validate(book)

    def get_book(self, book_id: int) -> BookResponse:
        stmt = select(Book).where(Book.id == book_id)
        book = self.db.execute(stmt).scalar_one_or_none()
        if not book:
            raise BookNotFoundException()
        return BookResponse.model_validate(book)

    def update_book(self, book_id: int, payload: BookUpdateRequest) -> BookResponse:
        stmt = select(Book).where(Book.id == book_id)
        book = self.db.execute(stmt).scalar_one_or_none()
        if not book:
            raise BookNotFoundException()

        if payload.department_id is not None and self.dept_repo:
            dept = self.dept_repo.get_by_id(payload.department_id)
            if not dept:
                raise DepartmentNotFoundException()

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

        self.db.commit()
        self.db.refresh(book)
        return BookResponse.model_validate(book)

    def delete_book(self, book_id: int) -> None:
        stmt = select(Book).where(Book.id == book_id)
        book = self.db.execute(stmt).scalar_one_or_none()
        if not book:
            raise BookNotFoundException()

        file_path = book.file_path
        self.db.delete(book)
        self.db.commit()
        self.file_storage.delete_file(file_path)

    def list_books(
        self,
        q: Optional[str] = None,
        department_id: Optional[int] = None,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookListResponse:
        stmt = select(Book)
        if q:
            stmt = stmt.where(Book.name.ilike(f"%{q}%"))
        if department_id:
            stmt = stmt.where(Book.department_id == department_id)
        if cursor is not None:
            stmt = stmt.where(Book.id > cursor)
        stmt = stmt.order_by(Book.id.asc()).limit(limit + 1)

        rows = self.db.execute(stmt).scalars().all()
        has_more = len(rows) > limit
        items_slice = rows[:limit]
        next_cursor = items_slice[-1].id if has_more and items_slice else None
        return BookListResponse(
            items=[BookResponse.model_validate(b) for b in items_slice],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def record_access(self, book_id: int, user_id: int) -> BookAccessResponse:
        stmt = select(Book).where(Book.id == book_id)
        book = self.db.execute(stmt).scalar_one_or_none()
        if not book:
            raise BookNotFoundException()

        access = BookAccess(
            user_id=user_id,
            book_id=book_id,
        )
        self.db.add(access)
        self.db.commit()
        self.db.refresh(access)
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

        rows = self.db.execute(stmt).all()
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
