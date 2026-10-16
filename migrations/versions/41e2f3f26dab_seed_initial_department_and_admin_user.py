"""seed_initial_department_and_admin_user

Revision ID: 41e2f3f26dab
Revises: cc697b72b99a
Create Date: 2026-10-16 12:37:06.597266

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41e2f3f26dab'
down_revision: Union[str, Sequence[str], None] = 'cc697b72b99a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed initial department and admin user."""
    op.execute(
        """
        INSERT INTO departments (id, name, created_at, updated_at)
        VALUES (1, 'Computer Science', now(), now())
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM users WHERE id = 1) THEN
                IF EXISTS (SELECT 1 FROM users WHERE email = 'admin@school.edu') THEN
                    INSERT INTO users (id, first_name, last_name, email, password_hash, role, is_active, department_id, created_at, updated_at)
                    VALUES (1, 'Admin', 'User', 'admin_dev@school.edu', 'mock_hash_for_dev', 'admin', true, 1, now(), now());
                ELSE
                    INSERT INTO users (id, first_name, last_name, email, password_hash, role, is_active, department_id, created_at, updated_at)
                    VALUES (1, 'Admin', 'User', 'admin@school.edu', 'mock_hash_for_dev', 'admin', true, 1, now(), now());
                END IF;
            ELSE
                UPDATE users SET role = 'admin', is_active = true, department_id = 1 WHERE id = 1;
            END IF;
        END $$;
        """
    )
    op.execute("SELECT setval('departments_id_seq', (SELECT COALESCE(MAX(id), 1) FROM departments));")
    op.execute("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users));")


def downgrade() -> None:
    """Remove seeded department and admin user."""
    op.execute("DELETE FROM book_access WHERE user_id = 1;")
    op.execute("DELETE FROM books WHERE uploaded_by = 1 OR department_id = 1;")
    op.execute("DELETE FROM users WHERE id = 1;")
    op.execute("DELETE FROM departments WHERE id = 1;")
