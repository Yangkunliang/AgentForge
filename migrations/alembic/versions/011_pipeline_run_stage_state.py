"""Add pipeline run and stage state tables

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-08
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(50), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(50), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("intent_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="planned"),
        sa.Column("current_stage_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_pipeline_runs_project_id", "pipeline_runs", ["project_id"])
    op.create_index("ix_pipeline_runs_session_id", "pipeline_runs", ["session_id"])
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])

    op.create_table(
        "pipeline_stage_states",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("pipeline_run_id", sa.String(50), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_id", sa.String(50), nullable=False),
        sa.Column("stage_name", sa.String(120), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("skip_reason", sa.String(200), nullable=True),
        sa.Column("confirmation_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_pipeline_stage_states_pipeline_run_id", "pipeline_stage_states", ["pipeline_run_id"])
    op.create_index("ix_pipeline_stage_states_stage_id", "pipeline_stage_states", ["stage_id"])
    op.create_index("ix_pipeline_stage_states_status", "pipeline_stage_states", ["status"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_stage_states_status")
    op.drop_index("ix_pipeline_stage_states_stage_id")
    op.drop_index("ix_pipeline_stage_states_pipeline_run_id")
    op.drop_table("pipeline_stage_states")
    op.drop_index("ix_pipeline_runs_status")
    op.drop_index("ix_pipeline_runs_session_id")
    op.drop_index("ix_pipeline_runs_project_id")
    op.drop_table("pipeline_runs")
