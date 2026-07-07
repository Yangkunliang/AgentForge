"""用户记忆模型(User Memory — 长期偏好与项目上下文)"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, JSON_VARIANT


class UserMemory(Base):
    """用户记忆表 — 持久化用户的长期偏好与项目上下文信息。

    这是 4 层记忆架构中的「User Memory」层,存储跨会话的长期信息,
    包括项目技术栈、编码风格偏好、项目结构笔记等。
    每个用户每个 category 只有一条记录(UniqueConstraint 约束)。
    """

    __tablename__ = "user_memories"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )  # 所属用户 ID

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        # project_context, preference, style_guide, tech_stack
    )  # 分类

    content: Mapped[str] = mapped_column(Text, nullable=False)  # 记忆内容

    extra_data: Mapped[dict] = mapped_column("metadata", JSON_VARIANT, nullable=False, default=dict)  # 额外数据

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
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
