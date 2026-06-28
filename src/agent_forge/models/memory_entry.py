"""会话记忆条目表 (MemoryEntry)

存储与任务(Task)关联的短期/场景记忆条目,记录 Agent 在任务执行过程中产生的
关键上下文信息(如决策点、中间结果等)。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MemoryEntry(Base):
    """会话记忆条目 — 存储任务执行过程中的短期/场景记忆。

    记录 Agent 在单个任务执行中产生的关键上下文信息(决策点、中间结果、
    临时笔记等),与特定 Task 绑定。与 SemanticEntry(跨会话语义记忆)不同,
    MemoryEntry 是任务级别的短期记忆。

    Fields:
        task_id: 关联的任务
        content: 记忆内容
        type: 记忆类型(默认 "general")
        created_at: 创建时间
    """

    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # 主键

    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # 关联的任务 ID

    content: Mapped[str] = mapped_column(Text, nullable=False)  # 记忆内容

    type: Mapped[str] = mapped_column(String(50), nullable=False, default="general")  # 记忆类型
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_memory_task_type", "task_id", "type"),
    )

    def __repr__(self) -> str:
        return f"<MemoryEntry(id={self.id}, task_id={self.task_id}, type={self.type})>"
