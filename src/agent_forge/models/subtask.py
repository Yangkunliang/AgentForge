"""子任务表 (SubTask)

存储从主任务(Task)分解出的子任务。Executor 将大任务拆解为多个可并行执行的子任务,
每个子任务分配给一个特定的 Agent 执行。
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as sa_Enum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:

    pass


class SubTaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(Base):
    """子任务表 — 从主任务(Task)分解出的可执行单元。

    Executor 将大任务拆解为多个 SubTask,每个子任务分配给一个特定 Agent 并行执行。
    子任务完成后汇总结果到父 Task。

    Fields:
        task_id: 所属父任务
        description: 子任务详细描述
        status: 当前状态(pending/processing/completed/failed)
        assigned_agent_id: 被分配的 Agent
        result: 子任务执行结果

    Relationships:
        task: 所属父任务
        assigned_agent: 被分配的 Agent
    """
    __tablename__ = "sub_tasks"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))  # 所属父任务 ID

    description: Mapped[str] = mapped_column(Text)  # 子任务详细描述

    status: Mapped[SubTaskStatus] = mapped_column(
        sa_Enum(SubTaskStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=SubTaskStatus.PENDING,
    )  # 状态: pending / processing / completed / failed

    assigned_agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)  # 被分配的 Agent ID

    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # 子任务执行结果

    # Relationships
    task = relationship("Task", back_populates="sub_tasks")
    assigned_agent = relationship("Agent", foreign_keys=[assigned_agent_id])

    def __repr__(self) -> str:
        return f"<SubTask id={self.id} status={self.status.value}>"
