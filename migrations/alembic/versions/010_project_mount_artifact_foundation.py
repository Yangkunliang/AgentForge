"""Add project, mount and artifact foundation

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-08
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tech_tags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "project_mounts",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(50), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mount_type", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="primary"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_project_mounts_project_id", "project_mounts", ["project_id"])

    op.add_column("sessions", sa.Column("project_id", sa.String(50), nullable=True))
    op.add_column("sessions", sa.Column("intent_type", sa.String(30), nullable=True))
    op.add_column("sessions", sa.Column("current_pipeline_run_id", sa.String(50), nullable=True))
    op.create_index("ix_sessions_project_id", "sessions", ["project_id"])
    op.create_foreign_key(
        "fk_sessions_project_id_projects",
        "sessions",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(50), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(50), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pipeline_run_id", sa.String(50), nullable=True),
        sa.Column("stage_state_id", sa.String(50), nullable=True),
        sa.Column("artifact_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(40), nullable=True),
        sa.Column("source_message_id", sa.String(50), sa.ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_artifacts_project_id", "artifacts", ["project_id"])
    op.create_index("ix_artifacts_session_id", "artifacts", ["session_id"])
    op.create_index("ix_artifacts_pipeline_run_id", "artifacts", ["pipeline_run_id"])
    op.create_index("ix_artifacts_stage_state_id", "artifacts", ["stage_state_id"])
    op.create_index("ix_artifacts_source_message_id", "artifacts", ["source_message_id"])

    _backfill_default_projects()


def downgrade() -> None:
    op.drop_index("ix_artifacts_source_message_id")
    op.drop_index("ix_artifacts_stage_state_id")
    op.drop_index("ix_artifacts_pipeline_run_id")
    op.drop_index("ix_artifacts_session_id")
    op.drop_index("ix_artifacts_project_id")
    op.drop_table("artifacts")

    op.drop_constraint("fk_sessions_project_id_projects", "sessions", type_="foreignkey")
    op.drop_index("ix_sessions_project_id")
    op.drop_column("sessions", "current_pipeline_run_id")
    op.drop_column("sessions", "intent_type")
    op.drop_column("sessions", "project_id")

    op.drop_index("ix_project_mounts_project_id")
    op.drop_table("project_mounts")
    op.drop_index("ix_projects_status")
    op.drop_index("ix_projects_user_id")
    op.drop_table("projects")


def _backfill_default_projects() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT DISTINCT user_id FROM sessions WHERE user_id IS NOT NULL AND project_id IS NULL")
    ).fetchall()

    for row in rows:
        user_id = row[0]
        project_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn.execute(
            sa.text(
                """
                INSERT INTO projects (id, user_id, name, description, tech_tags, status, created_at, updated_at)
                VALUES (:id, :user_id, '默认项目', '历史会话迁移自动创建的默认项目', :tech_tags, 'active', :now, :now)
                """
            ),
            {"id": project_id, "user_id": user_id, "tech_tags": "[]", "now": now},
        )
        conn.execute(
            sa.text("UPDATE sessions SET project_id = :project_id WHERE user_id = :user_id AND project_id IS NULL"),
            {"project_id": project_id, "user_id": user_id},
        )
