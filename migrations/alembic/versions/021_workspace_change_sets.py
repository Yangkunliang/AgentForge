"""Add authorized workspace change sets and file patches.

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: Union[str, Sequence[str], None] = "0020"
branch_labels = None
depends_on = None

JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "workspace_change_sets",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("task_graph_id", sa.String(50), nullable=False),
        sa.Column("task_node_id", sa.String(50), nullable=False),
        sa.Column("mount_id", sa.String(50), nullable=False),
        sa.Column("mount_root_sha256", sa.String(64), nullable=False),
        sa.Column("source_artifact_id", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="previewed"),
        sa.Column("apply_report", JSON_VARIANT, nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["task_graph_id"],
            ["task_graphs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_node_id"],
            ["task_nodes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mount_id"],
            ["project_mounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_id"],
            ["artifacts.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_workspace_change_sets_project_id",
        "workspace_change_sets",
        ["project_id"],
    )
    op.create_index(
        "ix_workspace_change_sets_task_graph_id",
        "workspace_change_sets",
        ["task_graph_id"],
    )
    op.create_index(
        "ix_workspace_change_sets_task_node_id",
        "workspace_change_sets",
        ["task_node_id"],
    )
    op.create_index(
        "ix_workspace_change_sets_mount_id",
        "workspace_change_sets",
        ["mount_id"],
    )
    op.create_index(
        "ix_workspace_change_sets_source_artifact_id",
        "workspace_change_sets",
        ["source_artifact_id"],
    )
    op.create_index(
        "ix_workspace_change_sets_status",
        "workspace_change_sets",
        ["status"],
    )

    op.create_table(
        "file_patches",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("change_set_id", sa.String(50), nullable=False),
        sa.Column("target_path", sa.String(2000), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False, server_default="upsert"),
        sa.Column("proposed_content", sa.Text(), nullable=False),
        sa.Column("unified_diff", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_exists", sa.Boolean(), nullable=False),
        sa.Column("base_sha256", sa.String(64), nullable=True),
        sa.Column("base_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_changes", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(30), nullable=False, server_default="previewed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["change_set_id"],
            ["workspace_change_sets.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "change_set_id",
            "target_path",
            name="uq_file_patches_change_set_path",
        ),
    )
    op.create_index("ix_file_patches_change_set_id", "file_patches", ["change_set_id"])
    op.create_index("ix_file_patches_status", "file_patches", ["status"])


def downgrade() -> None:
    op.drop_index("ix_file_patches_status", table_name="file_patches")
    op.drop_index("ix_file_patches_change_set_id", table_name="file_patches")
    op.drop_table("file_patches")
    op.drop_index("ix_workspace_change_sets_status", table_name="workspace_change_sets")
    op.drop_index(
        "ix_workspace_change_sets_source_artifact_id",
        table_name="workspace_change_sets",
    )
    op.drop_index("ix_workspace_change_sets_mount_id", table_name="workspace_change_sets")
    op.drop_index("ix_workspace_change_sets_task_node_id", table_name="workspace_change_sets")
    op.drop_index("ix_workspace_change_sets_task_graph_id", table_name="workspace_change_sets")
    op.drop_index("ix_workspace_change_sets_project_id", table_name="workspace_change_sets")
    op.drop_table("workspace_change_sets")
