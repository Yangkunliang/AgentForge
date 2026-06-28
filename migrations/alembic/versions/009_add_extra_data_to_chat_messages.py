"""add extra_data column to chat_messages

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chat_messages',
        sa.Column('extra_data', postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('chat_messages', 'extra_data')
