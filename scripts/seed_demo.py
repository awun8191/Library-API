"""Seed the deployed database with a small, realistic demo data set.

Run from the repository root, with the target database and the confirmation switch
in the environment:

    SEED_DEMO_CONFIRM=yes DATABASE_URL=postgresql+psycopg://... uv run python scripts/seed_demo.py

The script is additive and idempotent. A second run against the same database
creates no rows: departments and users are looked up before they are inserted,
books are skipped when their file hash is already stored, and the reading history
is written only when the student has none.

The six PDFs live in ``demo/books/`` and ship with the deployment, because the
production file system is read-only and ephemeral. A book row stores only the
file name, which is how the application reads it back through ``STORAGE_DIR``.
"""

import hashlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from integrations.database import DatabaseManager  # noqa: E402
from integrations.security import Argon2PasswordHasher  # noqa: E402
from modules.books.data import normalize_course_code  # noqa: E402
from schema.models import Book, BookAccess, Department, User  # noqa: E402

DEMO_BOOKS_DIR = ROOT / "demo" / "books"
DEFAULT_DEMO_PASSWORD = "demo-password-123"

DEPARTMENTS = [
    "Computer Science",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
]

USERS = [
    # (first, last, email, role, department)
    ("Admin", "User", "admin@school.edu", "admin", "Computer Science"),
    ("Ada", "Obi", "student@school.edu", "user", "Computer Science"),
]

BOOKS = [
    # (name, course_name, topic, course_code, department, file name)
    (
        "Introduction to Algorithms",
        "Algorithms",
        "Sorting and Graph Traversal",
        "CSC301",
        "Computer Science",
        "algorithms.pdf",
    ),
    (
        "Database Systems",
        "Database Systems",
        "Relational Design and SQL",
        "CSC305",
        "Computer Science",
        "databases.pdf",
    ),
    (
        "Circuit Theory I",
        "Circuit Theory I",
        "Kirchhoff's Laws and Network Analysis",
        "EEE211",
        "Electrical Engineering",
        "circuits.pdf",
    ),
    (
        "Signals and Systems",
        "Signals and Systems",
        "Convolution and Fourier Analysis",
        "EEE315",
        "Electrical Engineering",
        "signals.pdf",
    ),
    (
        "Engineering Thermodynamics",
        "Engineering Thermodynamics",
        "The First and Second Laws",
        "MEE301",
        "Mechanical Engineering",
        "thermodynamics.pdf",
    ),
    (
        "Structural Analysis",
        "Structural Analysis",
        "Beams and Trusses",
        "CVE311",
        "Civil Engineering",
        "structures.pdf",
    ),
]

READING_HISTORY = [
    # (file name, days ago, hours ago)
    ("algorithms.pdf", 4, 3),
    ("databases.pdf", 3, 6),
    ("thermodynamics.pdf", 1, 9),
    ("structures.pdf", 0, 2),
]

STUDENT_EMAIL = "student@school.edu"


class Totals:
    """Count the rows this run creates, per table."""

    def __init__(self) -> None:
        self.created = {"departments": 0, "users": 0, "books": 0, "book_access": 0}

    def count(self, table: str) -> None:
        self.created[table] += 1


def get_demo_password() -> str:
    return os.environ.get("DEMO_PASSWORD") or DEFAULT_DEMO_PASSWORD


def read_demo_pdf(file_name: str) -> tuple[bytes, str]:
    """Return the bytes and the SHA-256 hash of one demo PDF."""
    path = DEMO_BOOKS_DIR / file_name
    if not path.is_file():
        sys.exit(f"Refusing to seed: demo file is missing: {path}")
    content = path.read_bytes()
    if not content.startswith(b"%PDF-"):
        sys.exit(f"Refusing to seed: demo file is not a PDF: {path}")
    return content, hashlib.sha256(content).hexdigest()


def seed_departments(session: Session, totals: Totals) -> dict[str, Department]:
    departments: dict[str, Department] = {}
    for name in DEPARTMENTS:
        dept = session.execute(
            select(Department).where(Department.name == name)
        ).scalar_one_or_none()
        if dept is None:
            dept = Department(name=name)
            session.add(dept)
            session.flush()
            totals.count("departments")
        departments[name] = dept
    return departments


def seed_users(
    session: Session,
    departments: dict[str, Department],
    password: str,
    password_hash: str,
    hasher: Argon2PasswordHasher,
    totals: Totals,
) -> dict[str, User]:
    """Create each account, or repair it so the demo login works."""
    users: dict[str, User] = {}
    for first, last, email, role, dept_name in USERS:
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            user = User(
                first_name=first,
                last_name=last,
                email=email,
                password_hash=password_hash,
                role=role,
                is_active=True,
                department_id=departments[dept_name].id,
            )
            session.add(user)
            session.flush()
            totals.count("users")
        else:
            # Only touch the row when the demo password would not work, so a
            # second run writes nothing at all.
            if not hasher.verify(password, user.password_hash):
                user.password_hash = password_hash
            user.role = role
            user.is_active = True
            user.department_id = departments[dept_name].id
        users[email] = user
    return users


def seed_books(
    session: Session,
    departments: dict[str, Department],
    admin: User,
    totals: Totals,
) -> dict[str, Book]:
    """Insert one book per demo PDF, skipping any file hash already stored."""
    books: dict[str, Book] = {}
    for name, course_name, topic, course_code, dept_name, file_name in BOOKS:
        _content, file_hash = read_demo_pdf(file_name)
        book = session.execute(select(Book).where(Book.file_hash == file_hash)).scalar_one_or_none()
        if book is None:
            book = Book(
                name=name,
                course_name=course_name,
                topic=topic,
                course_code=normalize_course_code(course_code),
                file_hash=file_hash,
                file_path=file_name,
                uploaded_by=admin.id,
                department_id=departments[dept_name].id,
            )
            session.add(book)
            session.flush()
            totals.count("books")
        books[file_name] = book
    return books


def seed_reading_history(
    session: Session,
    student: User,
    books: dict[str, Book],
    totals: Totals,
) -> None:
    """Write the student's history once, over the last few days."""
    has_history = session.execute(
        select(BookAccess.id).where(BookAccess.user_id == student.id).limit(1)
    ).first()
    if has_history is not None:
        return

    now = datetime.now(UTC)
    for file_name, days_ago, hours_ago in READING_HISTORY:
        book = books[file_name]
        session.add(
            BookAccess(
                user_id=student.id,
                book_id=book.id,
                accessed_at=now - timedelta(days=days_ago, hours=hours_ago),
            )
        )
        totals.count("book_access")


def table_counts(session: Session) -> dict[str, int]:
    return {
        "departments": session.scalar(select(func.count()).select_from(Department)),
        "users": session.scalar(select(func.count()).select_from(User)),
        "books": session.scalar(select(func.count()).select_from(Book)),
        "book_access": session.scalar(select(func.count()).select_from(BookAccess)),
    }


def print_summary(totals: Totals, counts: dict[str, int], password: str) -> None:
    print("Demo seed complete.")
    for table in ("departments", "users", "books", "book_access"):
        print(f"  {table:<12} {counts[table]:>3} total, {totals.created[table]:>3} new")
    print(f"  login        admin@school.edu / {password}")


def main() -> int:
    if os.environ.get("SEED_DEMO_CONFIRM") != "yes":
        print(
            "Refusing to seed: set SEED_DEMO_CONFIRM=yes to write demo data. "
            "This script writes to whatever DATABASE_URL points at.",
            file=sys.stderr,
        )
        return 2

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Refusing to seed: DATABASE_URL is not set.", file=sys.stderr)
        return 2

    password = get_demo_password()
    hasher = Argon2PasswordHasher()
    # Hash once: Argon2 is deliberately slow, and every demo account uses it.
    password_hash = hasher.hash(password)

    manager = DatabaseManager(database_url)
    session = next(manager.get_session())
    totals = Totals()
    try:
        departments = seed_departments(session, totals)
        users = seed_users(session, departments, password, password_hash, hasher, totals)
        books = seed_books(session, departments, users["admin@school.edu"], totals)
        seed_reading_history(session, users[STUDENT_EMAIL], books, totals)
        session.commit()
        print_summary(totals, table_counts(session), password)
        return 0
    except SQLAlchemyError as exc:
        session.rollback()
        print(f"Seeding failed and was rolled back: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()
        manager.close()


if __name__ == "__main__":
    sys.exit(main())
