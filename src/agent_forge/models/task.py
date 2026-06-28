"""任务表 (Task)

存储用户发起的需求任务,包括任务的分类、状态、优先级、成本追踪等。
一个 Task 对应一次完整的 AI 执行流程(可能分解为多个 SubTask)。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as sa_Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:

    from .conversation import Conversation
    from .subtask import SubTask
    from .task_execution import TaskExecution


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base, TimestampMixin):
    """任务表 — 存储用户发起的 AI 执行任务全生命周期数据。

    一个 Task 代表一次完整的需求交互(可能由用户的一条 Message 触发),
    可分解为多个 SubTask 并行执行,通过 trace_id 关联全链路追踪。

    Fields:
        title: 任务标题
        description: 任务详细描述
        status: 当前状态(pending/processing/completed/failed/cancelled)
        priority: 优先级(1-3,数字越大越优先)
        parent_id: 父任务 ID(用于任务分解后的父子关系)
        assignee_id: 指定负责人(用户),可为 None 由系统自动分配
        created_by: 创建者用户 ID
        result: 任务最终结果
        trace_id: 全链路追踪 ID
        completed_at: 完成时间
        total_cost_usd: 总 LLM 调用成本(美元)

    Relationships:
        user: 所属用户(通过 user_id 关联)
        assignee: 指派的执行人
        creator: 创建者
        parent: 父任务
        sub_tasks: 分解出的子任务列表
        executions: 执行记录列表
        conversations: Agent 间对话记录
    """
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True,
    )  # 所属用户 ID(用户自己的项目任务)

    title: Mapped[str] = mapped_column(String(255), default="")  # 任务标题
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # 任务详细描述

    status: Mapped[TaskStatus] = mapped_column(
        sa_Enum(TaskStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=TaskStatus.PENDING,
        nullable=False,
    )  # 任务状态

    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 优先级(1=中, 2=高, 3=最高)

    # 父子任务关系
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True,
    )  # 父任务 ID(任务分解后指向父 Task)

    assignee_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )  # 指定负责人用户 ID(None = 系统自动分配)

    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )  # 创建者用户 ID

    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # 任务执行结果

    trace_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)  # 全链路追踪 ID

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # 完成时间戳

    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 总 LLM 调用成本(美元)

    # Relationships
    user = relationship("User", back_populates="tasks", foreign_keys=[user_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    creator = relationship("User", foreign_keys=[created_by])
    parent = relationship("Task", remote_side=[id])
    sub_tasks: Mapped[list[SubTask]] = relationship(back_populates="task", cascade="all, delete-orphan")
    executions: Mapped[list[TaskExecution]] = relationship(back_populates="task", cascade="all, delete-orphan")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        # 复合索引
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status.value}>"
