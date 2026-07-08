"""Add GitHub OAuth credential storage

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, Sequence[str], None] = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_credentials",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_oauth_credentials_user_id", "oauth_credentials", ["user_id"])
    op.create_index("ix_oauth_credentials_provider", "oauth_credentials", ["provider"])

    op.create_table(
        "oauth_states",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(50), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("state", sa.String(160), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_oauth_states_user_id", "oauth_states", ["user_id"])
    op.create_index("ix_oauth_states_project_id", "oauth_states", ["project_id"])
    op.create_index("ix_oauth_states_provider", "oauth_states", ["provider"])
    op.create_index("ix_oauth_states_state", "oauth_states", ["state"], unique=True)
    op.create_index("ix_oauth_states_expires_at", "oauth_states", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_states_expires_at")
    op.drop_index("ix_oauth_states_state")
    op.drop_index("ix_oauth_states_provider")
    op.drop_index("ix_oauth_states_project_id")
    op.drop_index("ix_oauth_states_user_id")
    op.drop_table("oauth_states")

    op.drop_index("ix_oauth_credentials_provider")
    op.drop_index("ix_oauth_credentials_user_id")
    op.drop_table("oauth_credentials")
