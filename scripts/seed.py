"""Database seeding script for local development."""
from sqlalchemy import select, text

from core.config import get_settings
from integrations.database import get_db_manager
from schema.models import Department, User


def seed_database():
    """Seed initial department and admin user safely using SQLAlchemy ORM."""
    manager = get_db_manager(get_settings().database_url)
    session = next(manager.get_session())
    try:
        # Check or create Department 1
        stmt_dept = select(Department).where(Department.id == 1)
        dept = session.execute(stmt_dept).scalar_one_or_none()
        if not dept:
            dept = Department(id=1, name="Computer Science")
            session.add(dept)
        else:
            dept.name = "Computer Science"
        session.flush()

        # Check or create Admin User 1
        stmt_user = select(User).where(User.id == 1)
        user = session.execute(stmt_user).scalar_one_or_none()
        if not user:
            existing_email = session.execute(
                select(User).where(User.email == "admin@school.edu")
            ).scalar_one_or_none()
            email = "admin_dev@school.edu" if existing_email else "admin@school.edu"
            user = User(
                id=1,
                first_name="Admin",
                last_name="User",
                email=email,
                password_hash="mock_hash_for_dev",
                role="admin",
                is_active=True,
                department_id=dept.id,
            )
            session.add(user)
        else:
            user.role = "admin"
            user.is_active = True
            user.department_id = dept.id

        session.commit()

        # Synchronize PostgreSQL autoincrement sequences
        session.execute(
            text("SELECT setval('departments_id_seq', (SELECT COALESCE(MAX(id), 1) FROM departments))")
        )
        session.execute(
            text("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users))")
        )
        session.commit()
        print("Successfully seeded department (id=1) and admin user (id=1).")
    finally:
        session.close()
        manager.close()


if __name__ == "__main__":
    seed_database()
