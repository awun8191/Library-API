"""week3_rate_limit_counters

Revision ID: c4d8e2f15a7b
Revises: 9b7c41e0a2f3
Create Date: 2026-11-01 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8e2f15a7b'
down_revision: Union[str, Sequence[str], None] = '9b7c41e0a2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the rate limit counter table and its window index."""
    op.create_table(
        'rate_limit_counters',
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hits', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )
    op.create_index(
        'ix_rate_limit_counters_window_start',
        'rate_limit_counters',
        ['window_start'],
        unique=False,
    )


def downgrade() -> None:
    """Drop the rate limit counter table and its index."""
    op.drop_index('ix_rate_limit_counters_window_start', table_name='rate_limit_counters')
    op.drop_table('rate_limit_counters')
