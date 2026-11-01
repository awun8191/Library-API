"""Shared fixtures for the Library API test suite."""

import atexit
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set. Point it at an empty PostgreSQL database "
        "before you run the tests."
    )

TEST_SECRET_KEY = "test-secret-key-for-the-library-api-test-suite-0001"
DEFAULT_PASSWORD = "test-password-123"

# The application reads its settings at import time. Set the environment first.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = TEST_SECRET_KEY
os.environ["ENVIRONMENT"] = "development"
STORAGE_DIRECTORY = tempfile.mkdtemp(prefix="library-api-storage-")
os.environ["STORAGE_DIR"] = STORAGE_DIRECTORY
# Keep the limits out of the existing tests. Each rate limit test turns them on.
os.environ["RATE_LIMIT_BACKEND"] = "memory"
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Remove the directory even when a session fixture fails during setup.
atexit.register(shutil.rmtree, STORAGE_DIRECTORY, True)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from core.config import get_settings  # noqa: E402
from dependencies import get_db, get_token_issuer  # noqa: E402
from integrations.rate_limit import clear_rate_limit_stores  # noqa: E402
from integrations.security import Argon2PasswordHasher, JwtTokenIssuer  # noqa: E402
from main import app  # noqa: E402
from middleware import rate_limit as rate_limit_middleware  # noqa: E402
from modules.books.data import BookResponse  # noqa: E402
from modules.departments.data import DepartmentResponse  # noqa: E402
from modules.users.data import UserResponse  # noqa: E402
from schema.models import Book, Department, User  # noqa: E402
from tests.fakes import FakeRateLimitStore  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    """Register the markers of this project."""
    config.addinivalue_line("markers", "postgres_store: uses the real rate limit table")


def run_migrations() -> None:
    """Apply every migration to the test database. Repeat runs are safe."""
    environment = os.environ.copy()
    environment["DATABASE_URL"] = TEST_DATABASE_URL

    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"alembic upgrade head failed:\n{completed.stderr}")


def truncate_all_tables(engine: Engine) -> None:
    """Empty every application table and reset the identity columns."""
    with engine.begin() as connection:
        table_names = (
            connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            .scalars()
            .all()
        )
        # The migration bookkeeping table must keep its rows. Otherwise the next
        # migration run tries to create tables that already exist.
        targets = [name for name in table_names if name != "alembic_version"]
        if not targets:
            return
        quoted = ", ".join(f'"{name}"' for name in targets)
        connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def fresh_settings_cache() -> Generator[None]:
    """Drop the cached settings and token issuer so each test reads the test environment."""
    get_settings.cache_clear()
    get_token_issuer.cache_clear()
    clear_rate_limit_stores()
    yield
    get_settings.cache_clear()
    get_token_issuer.cache_clear()
    clear_rate_limit_stores()


@pytest.fixture
def rate_limit_store(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[FakeRateLimitStore]:
    """Give the middleware a fake store with a clock that a test can move."""
    store = FakeRateLimitStore()
    monkeypatch.setattr(rate_limit_middleware, "build_rate_limit_store", lambda settings: store)
    yield store
    store.reset()


@pytest.fixture(autouse=True)
def reset_rate_limit_state(
    rate_limit_store: FakeRateLimitStore,
) -> Generator[None]:
    """Start each test with no counters, in the fake store and in the memory store."""
    clear_rate_limit_stores()
    rate_limit_store.reset()
    yield
    clear_rate_limit_stores()
    rate_limit_store.reset()


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine]:
    """Provide an engine for the test database."""
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database(db_engine: Engine) -> Generator[None]:
    """Build the schema once per session and start from empty tables."""
    run_migrations()
    truncate_all_tables(db_engine)
    yield


@pytest.fixture(scope="session", autouse=True)
def storage_directory() -> Generator[Path]:
    """Give the session one temporary storage directory and remove it at the end."""
    directory = Path(STORAGE_DIRECTORY)
    directory.mkdir(parents=True, exist_ok=True)
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def db_session(db_engine: Engine, migrated_database: None) -> Generator[Session]:
    """Bind a session to a transaction and roll the transaction back after the test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient]:
    """Provide a test client that uses the transactional test session."""

    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def make_pdf() -> Callable[..., bytes]:
    """Build small PDF bytes. Each call carries a unique marker, so each hash differs."""

    def _make_pdf(marker: str | None = None) -> bytes:
        unique = marker if marker is not None else uuid.uuid4().hex
        document = (
            "%PDF-1.4\n"
            f"% marker {unique}\n"
            "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            "2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
            "trailer\n<< /Root 1 0 R >>\n"
            "%%EOF\n"
        )
        return document.encode("utf-8")

    return _make_pdf


@pytest.fixture
def make_user(db_session: Session) -> Callable[..., UserResponse]:
    """Insert a user with an Argon2 hash and return its public fields."""
    hasher = Argon2PasswordHasher()

    def _make_user(
        role: str = "user",
        is_active: bool = True,
        password: str | None = None,
        email: str | None = None,
        department_id: int | None = None,
        first_name: str = "Ada",
        last_name: str = "Obi",
    ) -> UserResponse:
        plain_password = password if password is not None else DEFAULT_PASSWORD
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email or f"user-{uuid.uuid4().hex[:12]}@school.edu",
            password_hash=hasher.hash(plain_password),
            role=role,
            is_active=is_active,
            department_id=department_id,
        )
        db_session.add(user)
        db_session.flush()
        return UserResponse.model_validate(user)

    return _make_user


@pytest.fixture
def make_department(db_session: Session) -> Callable[..., DepartmentResponse]:
    """Insert a department and return it."""

    def _make_department(name: str | None = None) -> DepartmentResponse:
        department = Department(name=name or f"Department {uuid.uuid4().hex[:8]}")
        db_session.add(department)
        db_session.flush()
        return DepartmentResponse.model_validate(department)

    return _make_department


@pytest.fixture
def make_book(
    db_session: Session,
    make_user: Callable[..., UserResponse],
    make_department: Callable[..., DepartmentResponse],
) -> Callable[..., BookResponse]:
    """Insert a book and return it. Missing values come from the other factories."""

    def _make_book(
        name: str = "Intro to Algorithms",
        course_name: str = "Data Structures",
        topic: str = "Sorting",
        course_code: str = "CSC201",
        department_id: int | None = None,
        uploaded_by: int | None = None,
        file_hash: str | None = None,
        file_path: str | None = None,
    ) -> BookResponse:
        if department_id is None:
            department_id = make_department().id
        if uploaded_by is None:
            uploaded_by = make_user(role="admin").id
        book = Book(
            name=name,
            course_name=course_name,
            topic=topic,
            course_code=course_code,
            file_hash=file_hash or uuid.uuid4().hex + uuid.uuid4().hex,
            file_path=file_path or f"{uuid.uuid4().hex}.pdf",
            uploaded_by=uploaded_by,
            department_id=department_id,
        )
        db_session.add(book)
        db_session.flush()
        return BookResponse.model_validate(book)

    return _make_book


@pytest.fixture
def auth_headers() -> Callable[[UserResponse], dict[str, str]]:
    """Build an Authorization header for a user with the test secret."""
    issuer = JwtTokenIssuer(
        secret_key=TEST_SECRET_KEY,
        algorithm="HS256",
        expire_minutes=60,
    )

    def _auth_headers(user: UserResponse) -> dict[str, str]:
        token, _ = issuer.issue(user.id)
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers
