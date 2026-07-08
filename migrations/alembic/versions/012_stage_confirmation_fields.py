"""Add stage confirmation fields

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-08
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pipeline_stage_states", sa.Column("confirmation_action", sa.String(30), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("confirmation_feedback", sa.String(2000), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("confirmation_resolved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("pipeline_stage_states", "confirmation_resolved_at")
    op.drop_column("pipeline_stage_states", "confirmation_feedback")
    op.drop_column("pipeline_stage_states", "confirmation_action")
