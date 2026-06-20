"""Task 模型"""

from __future__ import annotations

from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as sa_Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .conversation import Conversation
    from .subtask import SubTask
    from .task_execution import TaskExecution


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

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(sa_Enum(TaskStatus), default=TaskStatus.PENDING)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(sa_Enum(TaskPriority), default=TaskPriority.MEDIUM)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)

    completed_at: Mapped[str | None] = mapped_column(nullable=True)  # ISO datetime string

    # Relationships
    user = relationship("User", back_populates="tasks")
    sub_tasks: Mapped[list["SubTask"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    executions: Mapped[list["TaskExecution"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        # 复合索引
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status.value}>"
