"""Add skill engine fields: enabled, source_type, tags, icon_url, github_url; agent_skills.enabled

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # skills 表扩展字段
    op.add_column("skills", sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("skills", sa.Column("source_type", sa.String(20), nullable=True, server_default="builtin"))
    op.add_column("skills", sa.Column("icon_url", sa.String(500), nullable=True))
    op.add_column("skills", sa.Column("tags", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("skills", sa.Column("github_url", sa.String(500), nullable=True))

    # agent_skills 表扩展字段
    op.add_column("agent_skills", sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"))

    op.create_index("ix_skills_enabled", "skills", ["enabled"])
    op.create_index("ix_skills_source_type", "skills", ["source_type"])


def downgrade() -> None:
    op.drop_index("ix_skills_source_type")
    op.drop_index("ix_skills_enabled")
    op.drop_column("agent_skills", "enabled")
    op.drop_column("skills", "github_url")
    op.drop_column("skills", "tags")
    op.drop_column("skills", "icon_url")
    op.drop_column("skills", "source_type")
    op.drop_column("skills", "enabled")
