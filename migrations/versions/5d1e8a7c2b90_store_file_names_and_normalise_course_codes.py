"""store_file_names_and_normalise_course_codes

Revision ID: 5d1e8a7c2b90
Revises: 9b7c41e0a2f3
Create Date: 2026-10-24 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5d1e8a7c2b90'
down_revision: Union[str, Sequence[str], None] = '9b7c41e0a2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Keep only the file name in books.file_path and upper-case course codes."""
    op.execute(r"UPDATE books SET file_path = regexp_replace(file_path, '^.*[/\\]', '')")
    op.execute("UPDATE books SET course_code = upper(trim(course_code))")


def downgrade() -> None:
    """File names still resolve against the storage folder, so there is nothing to undo."""
    pass
