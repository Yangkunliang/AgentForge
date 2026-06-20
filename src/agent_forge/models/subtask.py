"""SubTask 模型"""

from __future__ import annotations

from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as sa_Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .agent import Agent
    from .task import Task


class SubTaskStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(Base):
    __tablename__ = "sub_tasks"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[SubTaskStatus] = mapped_column(sa_Enum(SubTaskStatus), default=SubTaskStatus.PENDING)
    assigned_agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="sub_tasks")
    assigned_agent = relationship("Agent", foreign_keys=[assigned_agent_id])

    def __repr__(self) -> str:
        return f"<SubTask id={self.id} status={self.status.value}>"
