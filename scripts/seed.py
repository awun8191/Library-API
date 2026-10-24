"""Seed the local database with dummy development data.

Run from the repository root after `alembic upgrade head`:

    uv run python scripts/seed.py

Safe to run more than once: existing rows are reused, never duplicated.
Creates 3 departments, an admin and a student, 3 dummy course-material PDFs
(written to Storage/) and one reading-history entry.
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import select, text  # noqa: E402

from core.config import get_settings  # noqa: E402
from integrations.database import get_db_manager  # noqa: E402
from integrations.security import Argon2PasswordHasher  # noqa: E402
from schema.models import Book, BookAccess, Department, User  # noqa: E402

STORAGE_DIR = ROOT / "Storage"
DEV_PASSWORD = "dev-password-123"

DEPARTMENTS = ["Computer Science", "Electrical Engineering", "Mechanical Engineering"]

USERS = [
    # (first, last, email, role, department)
    ("Admin", "User", "admin@school.edu", "admin", "Computer Science"),
    ("Ada", "Student", "student@school.edu", "user", "Computer Science"),
]

BOOKS = [
    # (name, course_name, topic, course_code, department)
    ("Data Structures Lecture Notes", "Data Structures", "Linked Lists and Trees", "CSC201", "Computer Science"),
    ("Intro to Databases Handout", "Database Systems", "Relational Model and SQL", "CSC305", "Computer Science"),
    ("Circuit Theory Past Questions", "Circuit Theory I", "Kirchhoff's Laws", "EEE211", "Electrical Engineering"),
]


def make_pdf(title: str) -> bytes:
    """Build a tiny, valid one-page PDF containing the title (dummy content only)."""
    safe = title.replace("(", "[").replace(")", "]")
    stream = f"BT /F1 18 Tf 72 720 Td ({safe}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def seed_database() -> None:
    settings = get_settings()
    if settings.environment != "development":
        # The seed resets account passwords to a known value, so never run it outside development.
        sys.exit("Refusing to seed: ENVIRONMENT is not 'development'.")
    manager = get_db_manager(settings.database_url)
    session = next(manager.get_session())
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        departments = {}
        for name in DEPARTMENTS:
            dept = session.execute(select(Department).where(Department.name == name)).scalar_one_or_none()
            if not dept:
                dept = Department(name=name)
                session.add(dept)
                session.flush()
            departments[name] = dept

        users = {}
        dev_password_hash = Argon2PasswordHasher().hash(DEV_PASSWORD)
        for first, last, email, role, dept_name in USERS:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if not user:
                user = User(
                    first_name=first,
                    last_name=last,
                    email=email,
                    password_hash=dev_password_hash,
                    role=role,
                    is_active=True,
                    department_id=departments[dept_name].id,
                )
                session.add(user)
                session.flush()
            else:
                user.password_hash = dev_password_hash
            users[email] = user

        admin = users["admin@school.edu"]
        books = []
        for name, course_name, topic, course_code, dept_name in BOOKS:
            content = make_pdf(f"{course_code} - {name}")
            file_hash = hashlib.sha256(content).hexdigest()
            book = session.execute(select(Book).where(Book.file_hash == file_hash)).scalar_one_or_none()
            if not book:
                file_name = f"seed-{course_code.lower()}.pdf"
                (STORAGE_DIR / file_name).write_bytes(content)
                book = Book(
                    name=name,
                    course_name=course_name,
                    topic=topic,
                    course_code=course_code,
                    file_hash=file_hash,
                    file_path=file_name,
                    uploaded_by=admin.id,
                    department_id=departments[dept_name].id,
                )
                session.add(book)
                session.flush()
            books.append(book)

        student = users["student@school.edu"]
        has_history = session.execute(
            select(BookAccess).where(BookAccess.user_id == student.id)
        ).first()
        if not has_history:
            session.add(BookAccess(user_id=student.id, book_id=books[0].id))

        session.commit()

        for table in ("departments", "users", "books", "book_access"):
            session.execute(
                text(f"SELECT setval('{table}_id_seq', (SELECT COALESCE(MAX(id), 1) FROM {table}))")
            )
        session.commit()
        print(f"Seeded {len(departments)} departments, {len(users)} users, {len(books)} books.")
        print(f"Development login: admin@school.edu or student@school.edu, password '{DEV_PASSWORD}'")
    finally:
        session.close()
        manager.close()


if __name__ == "__main__":
    seed_database()
