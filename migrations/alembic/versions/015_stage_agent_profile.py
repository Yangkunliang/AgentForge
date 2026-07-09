"""Add runtime AgentProfile trace fields to pipeline stages

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, Sequence[str], None] = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pipeline_stage_states", sa.Column("agent_profile_id", sa.String(50), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("agent_profile_name", sa.String(120), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("agent_profile_source", sa.String(30), nullable=True))
    op.create_index("ix_pipeline_stage_states_agent_profile_id", "pipeline_stage_states", ["agent_profile_id"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_stage_states_agent_profile_id", table_name="pipeline_stage_states")
    op.drop_column("pipeline_stage_states", "agent_profile_source")
    op.drop_column("pipeline_stage_states", "agent_profile_name")
    op.drop_column("pipeline_stage_states", "agent_profile_id")
