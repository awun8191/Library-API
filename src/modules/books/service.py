"""Book resource business rules, orchestration, and use cases."""
import hashlib
from typing import Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from core.exceptions import (
    BookNotFoundException,
    DepartmentNotFoundException,
    DuplicateFileException,
    FileNotFoundException,
    FileUploadException,
)
from core.repository import FileStorageRepository
from modules.books.data import (
    BookAccessHistoryResponse,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)
from modules.books.repository import BookRepository
from modules.departments.repository import DepartmentRepository

PDF_MAGIC = b"%PDF-"


class BookService:
    def __init__(
        self,
        book_repo: BookRepository,
        file_storage: FileStorageRepository,
        dept_repo: Optional[DepartmentRepository] = None,
    ):
        self.book_repo = book_repo
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
        if not content.startswith(PDF_MAGIC):
            raise FileUploadException("Only PDF files are allowed")

        file_hash = hashlib.sha256(content).hexdigest()
        file_path = await self.file_storage.store_file(content)

        try:
            return self.book_repo.upload_book(
                name=name,
                course_name=course_name,
                topic=topic,
                course_code=course_code,
                department_id=department_id,
                file_hash=file_hash,
                file_path=file_path,
                uploaded_by=uploaded_by,
            )
        except IntegrityError as exc:
            self.file_storage.delete_file(file_path)
            existing = self.book_repo.find_by_file_hash(file_hash)
            if existing is not None:
                raise DuplicateFileException(
                    f"This document is already uploaded as '{existing.name}'"
                ) from exc
            raise
        except Exception:
            self.file_storage.delete_file(file_path)
            raise

    def get_book(self, book_id: int) -> BookResponse:
        book = self.book_repo.read_book(book_id)
        if not book:
            raise BookNotFoundException()
        return book

    def open_book(self, book_id: int, user_id: int) -> Tuple[str, BookResponse]:
        """Record the access and return the stored path with the book details."""
        book = self.book_repo.read_book(book_id)
        if not book:
            raise BookNotFoundException()

        stored_path = self.book_repo.read_file_path(book_id)
        if not stored_path:
            raise FileNotFoundException()

        file_path = self.file_storage.get_file_path(stored_path)
        self.book_repo.record_access(book_id=book_id, user_id=user_id)
        return file_path, book

    def update_book(self, book_id: int, payload: BookUpdateRequest) -> BookResponse:
        if payload.department_id is not None and self.dept_repo:
            dept = self.dept_repo.get_by_id(payload.department_id)
            if not dept:
                raise DepartmentNotFoundException()

        updated = self.book_repo.update_book(book_id, payload)
        if not updated:
            raise BookNotFoundException()
        return updated

    def delete_book(self, book_id: int) -> None:
        file_path = self.book_repo.delete_book(book_id)
        if not file_path:
            raise BookNotFoundException()
        self.file_storage.delete_file(file_path)

    def list_books(
        self,
        q: Optional[str] = None,
        department_id: Optional[int] = None,
        course_code: Optional[str] = None,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookListResponse:
        return self.book_repo.list_books(
            q=q,
            department_id=department_id,
            course_code=course_code,
            cursor=cursor,
            limit=limit,
        )

    def get_user_access_history(
        self,
        user_id: int,
        cursor: Optional[int] = None,
        limit: int = 10,
    ) -> BookAccessHistoryResponse:
        return self.book_repo.get_user_access_history(
            user_id=user_id,
            cursor=cursor,
            limit=limit,
        )
