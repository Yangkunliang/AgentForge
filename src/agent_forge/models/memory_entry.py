"""记忆条目模型"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MemoryEntry(Base):
    """记忆条目"""

    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_memory_task_type", "task_id", "type"),
    )

    def __repr__(self) -> str:
        return f"<MemoryEntry(id={self.id}, task_id={self.task_id}, type={self.type})>"