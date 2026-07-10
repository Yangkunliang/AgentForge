"""Add evaluation feedback events

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, Sequence[str], None] = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_events",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(50), nullable=True),
        sa.Column("pipeline_run_id", sa.String(50), nullable=True),
        sa.Column("stage_id", sa.String(50), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="success"),
        sa.Column("agent_profile_id", sa.String(50), nullable=True),
        sa.Column("agent_profile_name", sa.String(120), nullable=True),
        sa.Column("model_route_key", sa.String(80), nullable=True),
        sa.Column("model_route_name", sa.String(120), nullable=True),
        sa.Column("model_name", sa.String(160), nullable=True),
        sa.Column("skill_name", sa.String(120), nullable=True),
        sa.Column("tool_name", sa.String(120), nullable=True),
        sa.Column("artifact_id", sa.String(50), nullable=True),
        sa.Column("delivery_channel", sa.String(40), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_eval_events_project_id", "eval_events", ["project_id"])
    op.create_index("ix_eval_events_pipeline_run_id", "eval_events", ["pipeline_run_id"])
    op.create_index("ix_eval_events_stage_id", "eval_events", ["stage_id"])
    op.create_index("ix_eval_events_event_type", "eval_events", ["event_type"])
    op.create_index("ix_eval_events_status", "eval_events", ["status"])
    op.create_index("ix_eval_events_agent_profile_id", "eval_events", ["agent_profile_id"])
    op.create_index("ix_eval_events_model_route_key", "eval_events", ["model_route_key"])
    op.create_index("ix_eval_events_skill_name", "eval_events", ["skill_name"])
    op.create_index("ix_eval_events_artifact_id", "eval_events", ["artifact_id"])


def downgrade() -> None:
    op.drop_index("ix_eval_events_artifact_id", table_name="eval_events")
    op.drop_index("ix_eval_events_skill_name", table_name="eval_events")
    op.drop_index("ix_eval_events_model_route_key", table_name="eval_events")
    op.drop_index("ix_eval_events_agent_profile_id", table_name="eval_events")
    op.drop_index("ix_eval_events_status", table_name="eval_events")
    op.drop_index("ix_eval_events_event_type", table_name="eval_events")
    op.drop_index("ix_eval_events_stage_id", table_name="eval_events")
    op.drop_index("ix_eval_events_pipeline_run_id", table_name="eval_events")
    op.drop_index("ix_eval_events_project_id", table_name="eval_events")
    op.drop_table("eval_events")
