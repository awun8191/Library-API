"""Integration tests for the book upload, read, update, and delete endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from modules.books.data import BookResponse
from schema.models import Book

BOOKS_URL = "/api/v1/books"


def upload_book(
    client: TestClient,
    headers: dict,
    department_id: int,
    content: bytes,
    name: str = "Intro to Algorithms",
    course_name: str = "Data Structures",
    topic: str = "Sorting",
    course_code: str = "CSC201",
):
    """Post one PDF to the upload endpoint with fixed metadata."""
    return client.post(
        BOOKS_URL,
        data={
            "name": name,
            "course_name": course_name,
            "topic": topic,
            "course_code": course_code,
            "department_id": str(department_id),
        },
        files={"file": ("course-notes.pdf", content, "application/pdf")},
        headers=headers,
    )


def stored_file_path(db_session, book_id: int) -> str:
    """Read the stored file path of a book from the database."""
    db_session.expire_all()
    return db_session.execute(select(Book.file_path).where(Book.id == book_id)).scalar_one()


def test_admin_upload_returns_201_with_file_url(
    client: TestClient, make_user, make_department, make_pdf, auth_headers
) -> None:
    admin = make_user(role="admin")
    department = make_department(name="Computer Science")

    response = upload_book(client, auth_headers(admin), department.id, make_pdf("upload-ok"))

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Intro to Algorithms"
    assert body["course_name"] == "Data Structures"
    assert body["topic"] == "Sorting"
    assert body["course_code"] == "CSC201"
    assert body["department_id"] == department.id
    assert body["file_url"] == f"/api/v1/books/{body['id']}/file"


def test_student_upload_returns_403(
    client: TestClient, make_user, make_department, make_pdf, auth_headers
) -> None:
    student = make_user(role="user")
    department = make_department()

    response = upload_book(client, auth_headers(student), department.id, make_pdf("student-upload"))

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "FORBIDDEN"
    assert body["message"] == "Admin access required"


def test_upload_without_a_token_returns_401(client: TestClient, make_department, make_pdf) -> None:
    department = make_department()

    response = upload_book(client, {}, department.id, make_pdf("no-token"))

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_upload_of_a_non_pdf_returns_400(
    client: TestClient, make_user, make_department, auth_headers
) -> None:
    admin = make_user(role="admin")
    department = make_department()

    response = upload_book(client, auth_headers(admin), department.id, b"not a pdf at all")

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "FILE_UPLOAD_FAILED"
    assert body["message"] == "Only PDF files are allowed"


def test_upload_with_an_unknown_department_returns_404(
    client: TestClient, make_user, make_pdf, auth_headers
) -> None:
    admin = make_user(role="admin")

    response = upload_book(client, auth_headers(admin), 987654, make_pdf("no-dept"))

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "DEPARTMENT_NOT_FOUND"
    assert body["message"] == "Department not found"


def test_duplicate_upload_returns_409_and_names_the_existing_book(
    client: TestClient, make_user, make_department, make_pdf, auth_headers
) -> None:
    admin = make_user(role="admin")
    department = make_department()
    content = make_pdf("duplicate")
    upload_book(client, auth_headers(admin), department.id, content, name="First Copy")

    response = upload_book(client, auth_headers(admin), department.id, content, name="Second Copy")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "DUPLICATE_FILE"
    assert "First Copy" in body["message"]


def test_get_book_returns_the_book(client: TestClient, make_book, make_department) -> None:
    department = make_department()
    book = make_book(name="Linear Algebra", department_id=department.id)

    response = client.get(f"{BOOKS_URL}/{book.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == book.id
    assert body["name"] == "Linear Algebra"
    assert body["file_url"] == f"/api/v1/books/{book.id}/file"


def test_get_unknown_book_returns_404(client: TestClient) -> None:
    response = client.get(f"{BOOKS_URL}/987654")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "BOOK_NOT_FOUND"
    assert body["message"] == "Book not found"


def test_delete_removes_the_row_and_the_stored_file(
    client: TestClient,
    make_user,
    make_department,
    make_pdf,
    auth_headers,
    db_session,
    storage_directory,
) -> None:
    admin = make_user(role="admin")
    department = make_department()
    upload = upload_book(client, auth_headers(admin), department.id, make_pdf("delete-me"))
    book_id = upload.json()["id"]
    file_path = Path(storage_directory) / stored_file_path(db_session, book_id)
    assert file_path.is_file()

    response = client.delete(f"{BOOKS_URL}/{book_id}", headers=auth_headers(admin))

    assert response.status_code == 204
    assert response.content == b""
    assert not file_path.exists()
    db_session.expire_all()
    assert db_session.execute(select(Book).where(Book.id == book_id)).scalar_one_or_none() is None


def test_delete_unknown_book_returns_404(client: TestClient, make_user, auth_headers) -> None:
    admin = make_user(role="admin")

    response = client.delete(f"{BOOKS_URL}/987654", headers=auth_headers(admin))

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "BOOK_NOT_FOUND"


def test_patch_updates_one_field_and_keeps_the_rest(
    client: TestClient, make_user, make_book, auth_headers
) -> None:
    admin = make_user(role="admin")
    book: BookResponse = make_book(
        name="Intro to Algorithms", course_name="Data Structures", topic="Sorting"
    )

    response = client.patch(
        f"{BOOKS_URL}/{book.id}", json={"name": "Advanced Algorithms"}, headers=auth_headers(admin)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Advanced Algorithms"
    assert body["course_name"] == "Data Structures"
    assert body["topic"] == "Sorting"
    assert body["course_code"] == book.course_code


def test_patch_by_a_student_returns_403(
    client: TestClient, make_user, make_book, auth_headers
) -> None:
    student = make_user(role="user")
    book = make_book()

    response = client.patch(
        f"{BOOKS_URL}/{book.id}", json={"name": "Student Edit"}, headers=auth_headers(student)
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_patch_unknown_book_returns_404(client: TestClient, make_user, auth_headers) -> None:
    admin = make_user(role="admin")

    response = client.patch(
        f"{BOOKS_URL}/987654", json={"name": "Missing"}, headers=auth_headers(admin)
    )

    assert response.status_code == 404
    assert response.json()["code"] == "BOOK_NOT_FOUND"
