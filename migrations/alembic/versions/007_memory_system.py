"""add memory system tables

Revision ID: 007_memory_system
Revises: 0006
Create Date: 2026-06-25

Adds:
- semantic_entries: cross-session semantic memory with pgvector
- user_memories: per-user persistent preferences and context
- indexes on chat_messages for full-text search (episodic memory)
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import alembic


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Create semantic_entries table
    op.create_table(
        "semantic_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column(
            "metadata",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # semantic_entries indexes
    op.create_index(
        "ix_semantic_user_category",
        "semantic_entries",
        ["user_id", "category"],
    )
    op.create_index(
        "ix_semantic_deleted",
        "semantic_entries",
        ["deleted"],
    )
    op.create_index(
        "ix_semantic_task",
        "semantic_entries",
        ["task_id"],
    )

    # 3. Create user_memories table
    op.create_table(
        "user_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_user_memory_user",
        "user_memories",
        ["user_id"],
    )
    op.create_index(
        "ix_user_memory_user_time",
        "user_memories",
        ["user_id", "updated_at"],
    )
    op.create_unique_constraint(
        "uq_user_memory_category",
        "user_memories",
        ["user_id", "category"],
    )

    # 4. Add full-text search support for chat_messages (episodic memory)
    # Create GIN index for full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_chat_messages_content_fts
        ON chat_messages USING gin(to_tsvector('english', content))
    """)


def downgrade() -> None:
    # Remove full-text index
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_content_fts")

    # Drop user_memories
    op.drop_constraint("uq_user_memory_category", "user_memories", type_="unique")
    op.drop_index("ix_user_memory_user_time", table_name="user_memories")
    op.drop_index("ix_user_memory_user", table_name="user_memories")
    op.drop_table("user_memories")

    # Drop semantic_entries
    op.drop_index("ix_semantic_task", table_name="semantic_entries")
    op.drop_index("ix_semantic_deleted", table_name="semantic_entries")
    op.drop_index("ix_semantic_user_category", table_name="semantic_entries")
    op.drop_table("semantic_entries")
