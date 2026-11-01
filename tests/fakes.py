"""In-memory test doubles for the repository and storage contracts."""

import math
import time
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from core.exceptions import FileNotFoundException
from core.repository import RateLimitHit
from modules.books.data import (
    BookAccessHistoryResponse,
    BookAccessItemResponse,
    BookAccessResponse,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)
from modules.departments.data import DepartmentResponse
from modules.users.data import UserCredentials, UserResponse, UserUpdateRequest


def build_integrity_error() -> IntegrityError:
    """Build the error that the database raises for a duplicate unique key."""
    return IntegrityError(
        "INSERT INTO table (column) VALUES (%s)",
        {},
        Exception("duplicate key value violates unique constraint"),
    )


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


class FakeFileStorage:
    """Keep stored files in memory."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.store_calls: list[bytes] = []
        self.deleted_paths: list[str] = []

    def seed(self, file_path: str, content: bytes) -> None:
        """Put a file in the store without a store call."""
        self.files[file_path] = content

    def store_file(self, content: bytes) -> str:
        file_path = f"/memory/{len(self.store_calls) + 1}.pdf"
        self.files[file_path] = content
        self.store_calls.append(content)
        return file_path

    def get_file_path(self, file_path: str) -> str:
        if file_path not in self.files:
            raise FileNotFoundException()
        return file_path

    def delete_file(self, file_path: str) -> bool:
        self.deleted_paths.append(file_path)
        return self.files.pop(file_path, None) is not None


class FakeBookRepository:
    """Keep books and access records in memory."""

    def __init__(self) -> None:
        self.books: dict[int, BookResponse] = {}
        self.file_paths: dict[int, str] = {}
        self.hashes: dict[str, int] = {}
        self.accesses: list[BookAccessResponse] = []
        self.list_calls: list[dict] = []
        self._next_id = 1

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
        if file_hash in self.hashes:
            raise build_integrity_error()

        book = BookResponse(
            id=self._next_id,
            name=name,
            course_name=course_name,
            topic=topic,
            course_code=course_code,
            department_id=department_id,
            created_at=_now(),
            updated_at=_now(),
        )
        self._next_id += 1
        self.books[book.id] = book
        self.file_paths[book.id] = file_path
        self.hashes[file_hash] = book.id
        return book

    def read_book(self, book_id: int) -> BookResponse | None:
        return self.books.get(book_id)

    def read_file_path(self, book_id: int) -> str | None:
        return self.file_paths.get(book_id)

    def read_book_with_file(self, book_id: int):
        book = self.books.get(book_id)
        file_path = self.file_paths.get(book_id)
        if book is None or file_path is None:
            return None
        return book, file_path

    def find_by_file_hash(self, file_hash: str) -> BookResponse | None:
        book_id = self.hashes.get(file_hash)
        if book_id is None:
            return None
        return self.books.get(book_id)

    def update_book(self, book_id: int, payload: BookUpdateRequest) -> BookResponse | None:
        book = self.books.get(book_id)
        if book is None:
            return None

        changes = {
            field: value for field, value in payload.model_dump().items() if value is not None
        }
        updated = book.model_copy(update={**changes, "updated_at": _now()})
        self.books[book_id] = updated
        return updated

    def delete_book(self, book_id: int) -> str | None:
        book = self.books.pop(book_id, None)
        if book is None:
            return None

        file_path = self.file_paths.pop(book_id, None)
        self.hashes = {
            file_hash: stored_id
            for file_hash, stored_id in self.hashes.items()
            if stored_id != book_id
        }
        return file_path

    def list_books(
        self,
        q: str | None = None,
        department_id: int | None = None,
        course_code: str | None = None,
        cursor: int | None = None,
        limit: int = 10,
    ) -> BookListResponse:
        self.list_calls.append(
            {
                "q": q,
                "department_id": department_id,
                "course_code": course_code,
                "cursor": cursor,
                "limit": limit,
            }
        )
        items = list(self.books.values())[:limit]
        return BookListResponse(items=items, next_cursor=None, has_more=False)

    def record_access(self, book_id: int, user_id: int) -> BookAccessResponse:
        access = BookAccessResponse(
            id=len(self.accesses) + 1,
            user_id=user_id,
            book_id=book_id,
            accessed_at=_now(),
        )
        self.accesses.append(access)
        return access

    def get_user_access_history(
        self,
        user_id: int,
        cursor: int | None = None,
        limit: int = 10,
    ) -> BookAccessHistoryResponse:
        rows = [access for access in self.accesses if access.user_id == user_id]
        items = [
            BookAccessItemResponse(
                id=access.id,
                book_id=access.book_id,
                book_name=self.books[access.book_id].name if access.book_id in self.books else None,
                course_code=(
                    self.books[access.book_id].course_code if access.book_id in self.books else None
                ),
                accessed_at=access.accessed_at,
            )
            for access in rows[:limit]
        ]
        return BookAccessHistoryResponse(items=items, next_cursor=None, has_more=False)


class FakeAuthRepository:
    """Keep accounts in memory."""

    def __init__(self) -> None:
        self.credentials: dict[str, UserCredentials] = {}
        self.users: dict[int, UserResponse] = {}
        self.created: list[dict] = []
        self._next_id = 1

    def add_user(
        self,
        email: str,
        password_hash: str,
        role: str = "user",
        is_active: bool = True,
        first_name: str = "Ada",
        last_name: str = "Obi",
        department_id: int | None = None,
    ) -> UserResponse:
        """Store an account without a create call."""
        user_id = self._next_id
        self._next_id += 1
        self.credentials[email.strip().lower()] = UserCredentials(
            id=user_id,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        user = UserResponse(
            id=user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            is_active=is_active,
            department_id=department_id,
        )
        self.users[user_id] = user
        return user

    def get_credentials_by_email(self, email: str) -> UserCredentials | None:
        return self.credentials.get(email.strip().lower())

    def create_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str,
        department_id: int | None = None,
    ) -> UserResponse:
        if email.strip().lower() in self.credentials:
            raise build_integrity_error()

        self.created.append(
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password_hash": password_hash,
                "department_id": department_id,
            }
        )
        return self.add_user(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            department_id=department_id,
        )


class FakeUserRepository:
    """Keep user profiles in memory."""

    def __init__(self) -> None:
        self.users: dict[int, UserResponse] = {}

    def get_by_id(self, user_id: int) -> UserResponse | None:
        return self.users.get(user_id)

    def update_user(self, user_id: int, payload: UserUpdateRequest) -> UserResponse | None:
        user = self.users.get(user_id)
        if user is None:
            return None

        changes = {
            field: value for field, value in payload.model_dump().items() if value is not None
        }
        updated = user.model_copy(update=changes)
        self.users[user_id] = updated
        return updated


class FakeDepartmentRepository:
    """Keep departments in memory."""

    def __init__(self) -> None:
        self.departments: dict[int, DepartmentResponse] = {}

    def add(self, name: str, department_id: int | None = None) -> DepartmentResponse:
        """Store a department without a database call."""
        new_id = department_id if department_id is not None else len(self.departments) + 1
        department = DepartmentResponse(id=new_id, name=name, created_at=_now(), updated_at=_now())
        self.departments[new_id] = department
        return department

    def list_departments(self) -> list[DepartmentResponse]:
        return list(self.departments.values())

    def get_by_id(self, department_id: int) -> DepartmentResponse | None:
        return self.departments.get(department_id)


class FakeRateLimitStore:
    """Keep rate limit counters in memory and let a test move the clock."""

    def __init__(self) -> None:
        self.clock: float = time.time()
        # Each value holds the hit count and the start of its window.
        self.counters: dict[str, tuple[int, float]] = {}
        self.prune_calls: list[int] = []

    def set_clock(self, value: float) -> None:
        """Move the clock to a fixed time."""
        self.clock = value

    def advance(self, seconds: float) -> None:
        """Move the clock forward."""
        self.clock += seconds

    def reset(self) -> None:
        """Forget every counter and start again from the real time."""
        self.counters.clear()
        self.prune_calls.clear()
        self.clock = time.time()

    def increment(self, key: str, window_seconds: int) -> RateLimitHit:
        window_start = math.floor(self.clock / window_seconds) * window_seconds
        hits, stored_start = self.counters.get(key, (0, window_start))
        if stored_start != window_start:
            hits = 0
        hits += 1
        self.counters[key] = (hits, window_start)
        return RateLimitHit(
            hits=hits,
            window_start=datetime.fromtimestamp(window_start, tz=UTC),
            window_seconds=window_seconds,
        )

    def prune(self, older_than_seconds: int) -> None:
        self.prune_calls.append(older_than_seconds)
        cutoff = self.clock - older_than_seconds
        stale = [key for key, (_, start) in self.counters.items() if start < cutoff]
        for key in stale:
            del self.counters[key]
