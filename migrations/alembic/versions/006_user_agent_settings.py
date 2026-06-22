"""add user_agent_settings table

Revision ID: 006_user_agent_settings
Revises: 005_agent_avatar
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_agent_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(100), nullable=False, server_default="CodeSoul"),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_user_agent_settings_user_id", "user_agent_settings", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_agent_settings_user_id", table_name="user_agent_settings")
    op.drop_table("user_agent_settings")
