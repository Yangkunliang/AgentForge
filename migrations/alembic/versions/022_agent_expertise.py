"""Add expertise (distilled capability) column to agents.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-26
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: Union[str, Sequence[str], None] = "0021"
branch_labels = None
depends_on = None

JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("expertise", JSON_VARIANT, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("agents", "expertise")
