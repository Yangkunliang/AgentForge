"""AI 助手表 (Agent)

定义平台可使用的 AI 助手(Agent)配置,包括模型选择、能力和状态管理。
每个 Agent 代表一个可调用的 AI 角色(如代码审查员、生成器等)。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:

    from .agent_skill import AgentSkill
    from .subtask import SubTask
    from .task_execution import TaskExecution


class AgentStatus(str):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Agent(Base, TimestampMixin):
    """AI 助手表 — 定义可调用的 AI 助手配置(角色、模型、能力、状态)。

    每个 Agent 代表一个有特定能力的 AI 角色,例如代码审查员、代码生成器等。
    Router 层根据任务类型选择匹配的 Agent 执行。

    关联关系:
        sub_tasks_assigned: 被分配到此 Agent 的子任务
        agent_skills: 此 Agent 绑定的技能列表
        executions: 此 Agent 执行过的任务执行记录
    """
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    name: Mapped[str] = mapped_column(String(100), unique=True)  # Agent 唯一名称,如 "CodeReviewer"
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)  # 能力标签列表,如 ["code_review", "generation"]
    model: Mapped[str] = mapped_column(String(100))  # 底层 LLM 模型名,如 "claude-sonnet-4-6"
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Agent 功能描述
    status: Mapped[str] = mapped_column(String(20), default=AgentStatus.ACTIVE)  # 状态: "active" / "inactive"
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 头像 URL

    # Relationships
    sub_tasks_assigned: Mapped[list[SubTask]] = relationship(
        "SubTask",
        foreign_keys="SubTask.assigned_agent_id",
        back_populates="assigned_agent",
    )
    agent_skills: Mapped[list[AgentSkill]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    executions: Mapped[list[TaskExecution]] = relationship(back_populates="agent")

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name}>"
