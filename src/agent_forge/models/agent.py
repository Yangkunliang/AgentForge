"""Agent 模型"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum as sa_Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .agent_skill import AgentSkill
    from .subtask import SubTask
    from .task_execution import TaskExecution


class AgentStatus(str):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    name: Mapped[str] = mapped_column(String(100), unique=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(100))  # LLM model name
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=AgentStatus.ACTIVE)

    # Relationships
    sub_tasks_assigned: Mapped[list["SubTask"]] = relationship(
        "SubTask",
        foreign_keys="SubTask.assigned_agent_id",
        back_populates="assigned_agent",
    )
    agent_skills: Mapped[list["AgentSkill"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    executions: Mapped[list["TaskExecution"]] = relationship(back_populates="agent")

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name}>"
