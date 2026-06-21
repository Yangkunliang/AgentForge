"""Task 模型"""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as sa_Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .agent import Agent
    from .conversation import Conversation
    from .subtask import SubTask
    from .task_execution import TaskExecution
    from .user import User


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        sa_Enum(TaskStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Parent / assignee
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True,
    )
    assignee_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )

    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="tasks", foreign_keys=[user_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    creator = relationship("User", foreign_keys=[created_by])
    parent = relationship("Task", remote_side=[id])
    sub_tasks: Mapped[list["SubTask"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    executions: Mapped[list["TaskExecution"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        # 复合索引
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status.value}>"
