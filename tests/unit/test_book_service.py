"""Unit tests for the book use cases."""

import hashlib
import io

import pytest
from fastapi import UploadFile

from core.exceptions import (
    BookNotFoundException,
    DepartmentNotFoundException,
    DuplicateFileException,
    FileTooLargeException,
    FileUploadException,
)
from modules.books.data import BookListResponse, BookUpdateRequest
from modules.books.service import BookService
from tests.fakes import FakeBookRepository, FakeDepartmentRepository, FakeFileStorage

PDF_BYTES = b"%PDF-1.4\n% unit test document\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def build_storage() -> FakeFileStorage:
    """Build an empty in-memory file store."""
    return FakeFileStorage()


def build_departments(department_id: int = 1) -> FakeDepartmentRepository:
    """Build a department store with one department."""
    departments = FakeDepartmentRepository()
    departments.add("Computer Science", department_id=department_id)
    return departments


def build_service(
    books: FakeBookRepository | None = None,
    storage: FakeFileStorage | None = None,
    departments: FakeDepartmentRepository | None = None,
    max_upload_bytes: int = 20 * 1024 * 1024,
) -> BookService:
    """Build the book service on top of the fakes."""
    return BookService(
        book_repo=books if books is not None else FakeBookRepository(),
        file_storage=storage if storage is not None else build_storage(),
        dept_repo=departments,
        max_upload_bytes=max_upload_bytes,
    )


def build_upload(content: bytes = PDF_BYTES) -> UploadFile:
    """Build an upload object for the given bytes."""
    return UploadFile(file=io.BytesIO(content), filename="course-notes.pdf")


def upload(service: BookService, content: bytes = PDF_BYTES, department_id: int = 1):
    """Call the upload use case with fixed metadata."""
    return service.upload_book(
        name="Intro to Algorithms",
        course_name="Data Structures",
        topic="Sorting",
        course_code="CSC201",
        department_id=department_id,
        file=build_upload(content),
        uploaded_by=1,
    )


def test_upload_of_a_non_pdf_raises_before_any_storage_write():
    storage = build_storage()
    service = build_service(storage=storage, departments=build_departments())

    with pytest.raises(FileUploadException):
        upload(service, content=b"plain text, not a pdf")

    assert storage.store_calls == []
    assert storage.files == {}


def test_upload_with_an_unknown_department_raises():
    storage = build_storage()
    service = build_service(storage=storage, departments=FakeDepartmentRepository())

    with pytest.raises(DepartmentNotFoundException):
        upload(service, department_id=404)

    assert storage.store_calls == []


def test_upload_stores_the_file_and_returns_the_book():
    storage = build_storage()
    books = FakeBookRepository()
    service = build_service(books=books, storage=storage, departments=build_departments())

    created = upload(service)

    assert created.name == "Intro to Algorithms"
    assert created.course_code == "CSC201"
    assert created.department_id == 1
    assert created.file_url == f"/api/v1/books/{created.id}/file"
    assert list(storage.files.values()) == [PDF_BYTES]
    assert books.read_book(created.id) is not None


def test_upload_of_a_duplicate_file_raises_and_deletes_the_stored_file():
    content = PDF_BYTES
    file_hash = hashlib.sha256(content).hexdigest()
    books = FakeBookRepository()
    existing = books.upload_book(
        name="Existing Notes",
        course_name="Data Structures",
        topic="Sorting",
        course_code="CSC201",
        department_id=1,
        file_hash=file_hash,
        file_path="/memory/existing.pdf",
        uploaded_by=1,
    )
    storage = build_storage()
    service = build_service(books=books, storage=storage, departments=build_departments())

    with pytest.raises(DuplicateFileException) as error:
        upload(service, content=content)

    assert existing.name in str(error.value)
    assert storage.files == {}
    assert storage.deleted_paths == ["/memory/1.pdf"]


def test_open_book_records_one_access_and_returns_the_file_path():
    books = FakeBookRepository()
    book = books.upload_book(
        name="Intro to Algorithms",
        course_name="Data Structures",
        topic="Sorting",
        course_code="CSC201",
        department_id=1,
        file_hash="a" * 64,
        file_path="/memory/1.pdf",
        uploaded_by=1,
    )
    storage = build_storage()
    storage.seed("/memory/1.pdf", PDF_BYTES)
    service = build_service(books=books, storage=storage)

    file_path, opened = service.open_book(book_id=book.id, user_id=5)

    assert file_path == "/memory/1.pdf"
    assert opened.id == book.id
    assert len(books.accesses) == 1
    assert books.accesses[0].user_id == 5
    assert books.accesses[0].book_id == book.id


def test_open_book_on_a_missing_book_raises():
    books = FakeBookRepository()
    service = build_service(books=books, storage=build_storage())

    with pytest.raises(BookNotFoundException):
        service.open_book(book_id=404, user_id=5)

    assert books.accesses == []


def test_delete_book_removes_the_stored_file():
    books = FakeBookRepository()
    book = books.upload_book(
        name="Intro to Algorithms",
        course_name="Data Structures",
        topic="Sorting",
        course_code="CSC201",
        department_id=1,
        file_hash="b" * 64,
        file_path="/memory/1.pdf",
        uploaded_by=1,
    )
    storage = build_storage()
    storage.seed("/memory/1.pdf", PDF_BYTES)
    service = build_service(books=books, storage=storage)

    service.delete_book(book.id)

    assert storage.deleted_paths == ["/memory/1.pdf"]
    assert storage.files == {}
    assert books.read_book(book.id) is None


def test_update_of_a_missing_book_raises():
    service = build_service(books=FakeBookRepository())

    with pytest.raises(BookNotFoundException):
        service.update_book(404, BookUpdateRequest(topic="Graphs"))


def test_upload_over_the_service_limit_raises_and_writes_nothing():
    storage = build_storage()
    service = build_service(storage=storage, departments=build_departments(), max_upload_bytes=16)

    with pytest.raises(FileTooLargeException) as error:
        upload(service)

    assert error.value.status_code == 413
    assert error.value.code == "FILE_TOO_LARGE"
    assert storage.store_calls == []
    assert storage.files == {}


def test_upload_at_the_service_limit_is_stored():
    storage = build_storage()
    service = build_service(
        storage=storage,
        departments=build_departments(),
        max_upload_bytes=len(PDF_BYTES),
    )

    created = upload(service)

    assert created.course_code == "CSC201"
    assert list(storage.files.values()) == [PDF_BYTES]


def test_list_books_forwards_the_filters():
    books = FakeBookRepository()
    service = build_service(books=books)

    result = service.list_books(
        q="algorithms",
        department_id=2,
        course_code="CSC201",
        cursor=4,
        limit=5,
    )

    assert isinstance(result, BookListResponse)
    assert books.list_calls == [
        {
            "q": "algorithms",
            "department_id": 2,
            "course_code": "CSC201",
            "cursor": 4,
            "limit": 5,
        }
    ]
