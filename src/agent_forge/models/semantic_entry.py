"""语义记忆条目模型（pgvector 向量存储）"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

if TYPE_CHECKING:
    from pgvector.sqlalchemy import Vector


class SemanticEntry(Base):
    """语义记忆条目 — 跨会话语义记忆，支持向量相似度检索

    embedding 列在 Alembic migration 中创建为 vector(N) 类型（pgvector extension）。
    运行时通过 pgvector.sqlalchemy.Vector 类型绑定。
    """

    __tablename__ = "semantic_entries"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        # decision, code, design, result, context, preference
    )

    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 向量存储：通过 pgvector extension 的 vector(N) 类型
    # embedding 列在 migration 中定义为 vector(1536)
    embedding: Mapped[list[float] | None] = mapped_column(
        nullable=True,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
        # 复合索引
        Index("ix_semantic_user_category", "user_id", "category"),
        Index("ix_semantic_deleted", "deleted"),
    )

    def __repr__(self) -> str:
        return f"<SemanticEntry(id={self.id}, category={self.category})>"
