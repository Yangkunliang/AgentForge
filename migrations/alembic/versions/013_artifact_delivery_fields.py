"""Add artifact delivery fields

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-08
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: Union[str, Sequence[str], None] = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artifacts",
        sa.Column("delivery_status", sa.String(30), nullable=False, server_default="pending"),
    )
    op.add_column("artifacts", sa.Column("delivery_target_path", sa.Text(), nullable=True))
    op.add_column("artifacts", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("artifacts", sa.Column("delivery_report", sa.JSON(), nullable=True))
    op.create_index("ix_artifacts_delivery_status", "artifacts", ["delivery_status"])


def downgrade() -> None:
    op.drop_index("ix_artifacts_delivery_status")
    op.drop_column("artifacts", "delivery_report")
    op.drop_column("artifacts", "delivered_at")
    op.drop_column("artifacts", "delivery_target_path")
    op.drop_column("artifacts", "delivery_status")
