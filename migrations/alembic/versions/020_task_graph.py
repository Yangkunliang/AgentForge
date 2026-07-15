"""Add structured pipeline task graphs.

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: Union[str, Sequence[str], None] = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_graphs",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("pipeline_run_id", sa.String(50), nullable=False),
        sa.Column("source_stage_state_id", sa.String(50), nullable=True),
        sa.Column("source_artifact_id", sa.String(50), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ready"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_stage_state_id"],
            ["pipeline_stage_states.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_id"],
            ["artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("pipeline_run_id", name="uq_task_graphs_pipeline_run_id"),
    )
    op.create_index("ix_task_graphs_project_id", "task_graphs", ["project_id"])
    op.create_index("ix_task_graphs_pipeline_run_id", "task_graphs", ["pipeline_run_id"])
    op.create_index(
        "ix_task_graphs_source_stage_state_id",
        "task_graphs",
        ["source_stage_state_id"],
    )
    op.create_index(
        "ix_task_graphs_source_artifact_id",
        "task_graphs",
        ["source_artifact_id"],
    )
    op.create_index("ix_task_graphs_status", "task_graphs", ["status"])

    op.create_table(
        "task_nodes",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("task_graph_id", sa.String(50), nullable=False),
        sa.Column("node_key", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("acceptance_criteria", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("target_files", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("verification_commands", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_graph_id"],
            ["task_graphs.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("task_graph_id", "node_key", name="uq_task_nodes_graph_key"),
        sa.UniqueConstraint(
            "task_graph_id",
            "order_index",
            name="uq_task_nodes_graph_order",
        ),
    )
    op.create_index("ix_task_nodes_task_graph_id", "task_nodes", ["task_graph_id"])
    op.create_index("ix_task_nodes_status", "task_nodes", ["status"])

    op.create_table(
        "task_node_dependencies",
        sa.Column("task_node_id", sa.String(50), primary_key=True),
        sa.Column("depends_on_node_id", sa.String(50), primary_key=True),
        sa.ForeignKeyConstraint(
            ["task_node_id"],
            ["task_nodes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["depends_on_node_id"],
            ["task_nodes.id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("task_node_dependencies")
    op.drop_index("ix_task_nodes_status", table_name="task_nodes")
    op.drop_index("ix_task_nodes_task_graph_id", table_name="task_nodes")
    op.drop_table("task_nodes")
    op.drop_index("ix_task_graphs_status", table_name="task_graphs")
    op.drop_index("ix_task_graphs_source_artifact_id", table_name="task_graphs")
    op.drop_index("ix_task_graphs_source_stage_state_id", table_name="task_graphs")
    op.drop_index("ix_task_graphs_pipeline_run_id", table_name="task_graphs")
    op.drop_index("ix_task_graphs_project_id", table_name="task_graphs")
    op.drop_table("task_graphs")
