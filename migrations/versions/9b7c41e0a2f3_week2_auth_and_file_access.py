"""week2_auth_and_file_access

Revision ID: 9b7c41e0a2f3
Revises: 41e2f3f26dab
Create Date: 2026-10-24 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b7c41e0a2f3'
down_revision: Union[str, Sequence[str], None] = '41e2f3f26dab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the stored file URL and constrain the user role."""
    op.drop_column('books', 'file_url')
    op.create_check_constraint('ck_users_role', 'users', "role IN ('admin', 'user')")


def downgrade() -> None:
    """Restore the stored file URL and remove the role constraint."""
    op.drop_constraint('ck_users_role', 'users', type_='check')
    op.add_column('books', sa.Column('file_url', sa.String(length=512), nullable=False, server_default=''))
    op.alter_column('books', 'file_url', server_default=None)
