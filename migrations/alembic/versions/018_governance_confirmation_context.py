"""Add governance confirmation context to pipeline stages

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, Sequence[str], None] = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pipeline_stage_states", sa.Column("confirmation_type", sa.String(80), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("confirmation_reason", sa.Text(), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("confirmation_impact_scope", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("pipeline_stage_states", sa.Column("confirmation_audit_payload", sa.JSON(), nullable=True, server_default="{}"))


def downgrade() -> None:
    op.drop_column("pipeline_stage_states", "confirmation_audit_payload")
    op.drop_column("pipeline_stage_states", "confirmation_impact_scope")
    op.drop_column("pipeline_stage_states", "confirmation_reason")
    op.drop_column("pipeline_stage_states", "confirmation_type")
