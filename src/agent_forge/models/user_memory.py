"""用户记忆模型（User Memory — 长期偏好与项目上下文）"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserMemory(Base):
    """用户记忆 — 持久化用户偏好和项目上下文"""

    __tablename__ = "user_memories"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        # project_context, preference, style_guide, tech_stack
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    extra_data: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_memory_category"),
        Index("ix_user_memory_user_time", "user_id", "updated_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<UserMemory(id={self.id}, user_id={self.user_id}, "
            f"category={self.category})>"
        )
