"""TaskExecution 模型"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum as sa_Enum, ForeignKey, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .agent import Agent
    from .skill import Skill
    from .task import Task


class ExecutionStatus(str):
    SUCCESS = "success"
    FAILED = "failed"


class TaskExecution(Base, TimestampMixin):
    __tablename__ = "task_executions"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    sub_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("sub_tasks.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    skill_id: Mapped[str | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )

    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    tokens_used: Mapped[dict] = mapped_column(JSON, default=dict)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.SUCCESS)
    user_feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)

    # Relationships
    task = relationship("Task", back_populates="executions")
    agent = relationship("Agent", back_populates="executions")
    skill = relationship("Skill", back_populates="executions")

    def __repr__(self) -> str:
        return f"<TaskExecution id={self.id} status={self.status}>"
