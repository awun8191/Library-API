"""Book resource business rules, orchestration, and use cases."""
import hashlib
import logging
from typing import Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from core.exceptions import (
    BookNotFoundException,
    DepartmentNotFoundException,
    DuplicateFileException,
    FileTooLargeException,
    FileUploadException,
)
from core.repository import FileStorageRepository
from modules.books.data import (
    BookAccessHistoryResponse,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
    normalize_course_code,
)
from modules.books.repository import BookRepository
from modules.departments.repository import DepartmentRepository

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"
CHUNK_SIZE = 1024 * 1024
DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class BookService:
    def __init__(
        self,
        book_repo: BookRepository,
        file_storage: FileStorageRepository,
        dept_repo: Optional[DepartmentRepository] = None,
        max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    ):
        self.book_repo = book_repo
        self.file_storage = file_storage
        self.dept_repo = dept_repo
        self.max_upload_bytes = max_upload_bytes

    def _read_pdf(self, file: UploadFile) -> Tuple[bytes, str]:
        """Read the upload in chunks, stop past the size limit, and hash it."""
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        size = 0
        file.file.seek(0)
        while chunk := file.file.read(CHUNK_SIZE):
            size += len(chunk)
            if size > self.max_upload_bytes:
                limit_mb = self.max_upload_bytes // (1024 * 1024)
                raise FileTooLargeException(f"File is larger than the {limit_mb} MB limit")
            digest.update(chunk)
            chunks.append(chunk)

        content = b"".join(chunks)
        if not content.startswith(PDF_MAGIC):
            raise FileUploadException("Only PDF files are allowed")
        return content, digest.hexdigest()

    def upload_book(
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

        content, file_hash = self._read_pdf(file)
        file_path = self.file_storage.store_file(content)

        try:
            return self.book_repo.upload_book(
                name=name,
                course_name=course_name,
                topic=topic,
                course_code=normalize_course_code(course_code),
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

    def open_book(
        self, book_id: int, user_id: int, record: bool = True
    ) -> Tuple[str, BookResponse]:
        """Return the stored path with the book details, recording the access when asked."""
        found = self.book_repo.read_book_with_file(book_id)
        if not found:
            raise BookNotFoundException()
        book, stored_name = found

        file_path = self.file_storage.get_file_path(stored_name)
        if record:
            self.book_repo.record_access(book_id=book_id, user_id=user_id)
        return file_path, book

    def update_book(self, book_id: int, payload: BookUpdateRequest) -> BookResponse:
        if "department_id" in payload.model_fields_set and self.dept_repo:
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
        try:
            removed = self.file_storage.delete_file(file_path)
        except OSError:
            removed = False
        if not removed:
            # The row is already gone; an orphaned or missing file is logged, not fatal.
            logger.warning("Stored file for deleted book %s was not removed: %s", book_id, file_path)

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
