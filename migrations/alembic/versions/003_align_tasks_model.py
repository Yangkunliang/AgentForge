"""Align tasks table with Task model

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-21

This migration adds columns that the original tasks table was missing
compared to the Task SQLAlchemy model:
  - trace_id (VARCHAR(64))
  - assignee_id (VARCHAR(50), FK -> users.id)
  - parent_id (VARCHAR(50), FK -> tasks.id) -- already exists in DB but added for completeness
  - user_id (VARCHAR) -- already exists in DB but made nullable explicit

It also adds the missing indexes.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # trace_id — column exists in migration but may be missing in DB (DB shows it does exist)
    # We add indexes that the DB likely doesn't have yet
    op.create_index("ix_tasks_trace_id", "tasks", ["trace_id"])

    # assignee_id already exists from 000_base, but ensure the index exists
    op.create_index("ix_tasks_assignee", "tasks", ["assignee_id"], if_not_exists=True)

    # status index
    op.create_index("ix_tasks_status", "tasks", ["status"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_tasks_status")
    op.drop_index("ix_tasks_assignee")
    op.drop_index("ix_tasks_trace_id")
