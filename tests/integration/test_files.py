"""Integration tests for the file download and access history endpoints."""

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from modules.books.data import BookResponse
from schema.models import BookAccess

HISTORY_URL = "/api/v1/users/me/access-history"


def store_book(
    make_book,
    storage_directory: Path,
    content: bytes,
    name: str = "Intro to Algorithms",
    course_code: str = "CSC201",
) -> tuple[BookResponse, Path]:
    """Create a book row with a real PDF on disk and return both."""
    file_name = f"{uuid.uuid4().hex}.pdf"
    file_path = storage_directory / file_name
    file_path.write_bytes(content)
    book = make_book(name=name, course_code=course_code, file_path=file_name)
    return book, file_path


def download(client: TestClient, book_id: int, headers: dict):
    """Request the stored PDF of a book."""
    return client.get(f"/api/v1/books/{book_id}/file", headers=headers)


def test_download_without_a_token_returns_401(
    client: TestClient, make_book, storage_directory, make_pdf
) -> None:
    book, _ = store_book(make_book, storage_directory, make_pdf("no-token"))

    response = download(client, book.id, {})

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_download_returns_the_pdf_stream(
    client: TestClient, make_user, make_book, storage_directory, make_pdf, auth_headers
) -> None:
    student = make_user(role="user")
    content = make_pdf("download-body")
    book, _ = store_book(make_book, storage_directory, content, name="Intro to Algorithms")

    response = download(client, book.id, auth_headers(student))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert response.content == content
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-disposition"].startswith("inline")


def test_one_download_records_exactly_one_access(
    client: TestClient, make_user, make_book, storage_directory, make_pdf, auth_headers, db_session
) -> None:
    student = make_user(role="user")
    book, _ = store_book(make_book, storage_directory, make_pdf("one-access"))

    response = download(client, book.id, auth_headers(student))

    assert response.status_code == 200
    db_session.expire_all()
    count = db_session.execute(
        select(func.count()).select_from(BookAccess).where(BookAccess.user_id == student.id)
    ).scalar_one()
    assert count == 1
    row = db_session.execute(
        select(BookAccess).where(BookAccess.user_id == student.id)
    ).scalar_one()
    assert row.book_id == book.id


def test_history_returns_the_recorded_access(
    client: TestClient, make_user, make_book, storage_directory, make_pdf, auth_headers
) -> None:
    student = make_user(role="user")
    book, _ = store_book(
        make_book, storage_directory, make_pdf("history-item"), name="Intro to Algorithms"
    )
    download(client, book.id, auth_headers(student))

    response = client.get(HISTORY_URL, headers=auth_headers(student))

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["book_id"] == book.id
    assert item["book_name"] == "Intro to Algorithms"
    assert item["course_code"] == "CSC201"
    assert item["file_url"] == f"/api/v1/books/{book.id}/file"


def test_download_of_an_unknown_book_returns_404(
    client: TestClient, make_user, auth_headers
) -> None:
    student = make_user(role="user")

    response = download(client, 987654, auth_headers(student))

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "BOOK_NOT_FOUND"
    assert body["message"] == "Book not found"


def test_download_when_the_stored_file_is_gone_returns_404(
    client: TestClient, make_user, make_book, storage_directory, make_pdf, auth_headers
) -> None:
    student = make_user(role="user")
    book, file_path = store_book(make_book, storage_directory, make_pdf("gone"))
    file_path.unlink()

    response = download(client, book.id, auth_headers(student))

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "FILE_NOT_FOUND"
    assert body["message"] == "File not found in storage"


def test_history_without_a_token_returns_401(client: TestClient) -> None:
    response = client.get(HISTORY_URL)

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_history_returns_only_caller_rows_newest_first(
    client: TestClient, make_user, make_book, storage_directory, make_pdf, auth_headers
) -> None:
    student = make_user(role="user")
    other = make_user(role="user")
    first_book, _ = store_book(make_book, storage_directory, make_pdf("first"), name="First")
    second_book, _ = store_book(
        make_book, storage_directory, make_pdf("second"), name="Second", course_code="CSC202"
    )
    other_book, _ = store_book(
        make_book, storage_directory, make_pdf("other"), name="Other", course_code="CSC203"
    )
    download(client, first_book.id, auth_headers(student))
    download(client, second_book.id, auth_headers(student))
    download(client, other_book.id, auth_headers(other))

    response = client.get(HISTORY_URL, headers=auth_headers(student))

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["book_id"] for item in items] == [second_book.id, first_book.id]
    assert [item["id"] for item in items] == sorted([item["id"] for item in items], reverse=True)


def test_history_pagination_walks_two_pages(
    client: TestClient, make_user, make_book, storage_directory, make_pdf, auth_headers
) -> None:
    student = make_user(role="user")
    first_book, _ = store_book(make_book, storage_directory, make_pdf("page-one"), name="First")
    second_book, _ = store_book(make_book, storage_directory, make_pdf("page-two"), name="Second")
    download(client, first_book.id, auth_headers(student))
    download(client, second_book.id, auth_headers(student))

    page = client.get(HISTORY_URL, params={"limit": 1}, headers=auth_headers(student)).json()
    assert len(page["items"]) == 1
    assert page["items"][0]["book_id"] == second_book.id
    assert page["has_more"] is True
    assert page["next_cursor"] is not None

    last = client.get(
        HISTORY_URL,
        params={"limit": 1, "cursor": page["next_cursor"]},
        headers=auth_headers(student),
    ).json()

    assert [item["book_id"] for item in last["items"]] == [first_book.id]
    assert last["has_more"] is False
    assert last["next_cursor"] is None
