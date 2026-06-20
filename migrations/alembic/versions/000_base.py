"""Initial migration: create all tables

Revision ID: 0001
Revises:
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 users 表
    op.create_table(
        "users",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("permissions", sa.JSON, nullable=False, default=list),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 创建 skills 表
    op.create_table(
        "skills",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("manifest", sa.JSON, nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="0.0.0"),
        sa.Column("entry_point", sa.String(255), nullable=True, server_default=""),
        sa.Column("dependencies", sa.JSON, nullable=True),
        sa.Column("installed_at", sa.String(50), nullable=True),
        sa.Column("created_by", sa.String(50), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 创建 agents 表
    op.create_table(
        "agents",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("config", sa.JSON, nullable=False, default=dict),
        sa.Column("capabilities", sa.JSON, nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(50), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 创建 agent_skills 关联表
    op.create_table(
        "agent_skills",
        sa.Column("agent_id", sa.String(50), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", sa.String(50), sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("config", sa.JSON, nullable=True),
    )

    # 创建 tasks 表
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("priority", sa.Integer, nullable=False, default=0),
        sa.Column("parent_id", sa.String(50), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("assignee_id", sa.String(50), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by", sa.String(50), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("total_cost_usd", sa.Float, nullable=False, default=0.0, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 创建 conversations 表
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("task_id", sa.String(50), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_id", sa.String(50), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 创建 messages 表
    op.create_table(
        "messages",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("conversation_id", sa.String(50), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 创建 execution_logs 表
    op.create_table(
        "execution_logs",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("trace_id", sa.String(50), nullable=False, unique=True),
        sa.Column("agent_id", sa.String(50), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_id", sa.String(50), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("input_data", sa.JSON, nullable=True),
        sa.Column("output_data", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 创建 api_keys 表
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("permissions", sa.JSON, nullable=False, default=list),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 创建 skill_installs 表
    op.create_table(
        "skill_installs",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("log", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 创建索引
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_agents_name", "agents", ["name"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_assignee", "tasks", ["assignee_id"])
    op.create_index("ix_execution_logs_trace_id", "execution_logs", ["trace_id"])
    op.create_index("ix_api_keys_user", "api_keys", ["user_id"])


def downgrade() -> None:
    # 删除索引
    op.drop_index("ix_api_keys_user")
    op.drop_index("ix_execution_logs_trace_id")
    op.drop_index("ix_tasks_assignee")
    op.drop_index("ix_tasks_status")
    op.drop_index("ix_agents_name")
    op.drop_index("ix_users_email")
    op.drop_index("ix_users_username")

    # 删除表（按依赖顺序）
    op.drop_table("api_keys")
    op.drop_table("execution_logs")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("tasks")
    op.drop_table("agent_skills")
    op.drop_table("agents")
    op.drop_table("skills")
    op.drop_table("users")
