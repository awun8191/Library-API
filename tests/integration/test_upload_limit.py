"""Integration tests for the upload size limit."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.config import get_settings
from schema.models import Book
from tests.integration.test_books import upload_book

MEGABYTE = 1024 * 1024


def set_upload_limit(monkeypatch: pytest.MonkeyPatch, megabytes: str) -> None:
    """Change the limit and drop the cached settings."""
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", megabytes)
    get_settings.cache_clear()


def count_books(db_session: Session) -> int:
    """Return the number of stored books."""
    db_session.expire_all()
    return db_session.execute(select(func.count()).select_from(Book)).scalar_one()


def test_an_upload_over_the_limit_returns_413(
    client: TestClient,
    db_session: Session,
    make_user,
    make_department,
    make_pdf,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_upload_limit(monkeypatch, "1")
    admin = make_user(role="admin")
    department = make_department()
    content = make_pdf("too-large") + b"0" * (2 * MEGABYTE)

    response = upload_book(client, auth_headers(admin), department.id, content)

    assert response.status_code == 413
    body = response.json()
    assert set(body) == {"message", "code"}
    assert body["code"] == "FILE_TOO_LARGE"
    assert response.headers["X-Request-ID"]
    assert count_books(db_session) == 0


def test_a_small_upload_passes_under_the_same_limit(
    client: TestClient, make_user, make_department, make_pdf, auth_headers, monkeypatch
) -> None:
    set_upload_limit(monkeypatch, "1")
    admin = make_user(role="admin")
    department = make_department()
    content = make_pdf("small") + b"0" * 1024

    response = upload_book(client, auth_headers(admin), department.id, content)

    assert response.status_code == 201
    assert response.json()["name"] == "Intro to Algorithms"
