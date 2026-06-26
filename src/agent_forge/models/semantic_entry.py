"""语义记忆条目模型（pgvector 向量存储）"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import NullType

from .base import Base

# pgvector 可选依赖：本地开发若未安装则降级为 NullType（不影响启动）
try:
    from pgvector.sqlalchemy import Vector as _Vector
    _VECTOR_TYPE = _Vector(1536)
except ImportError:
    _VECTOR_TYPE = NullType()


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

    extra_data: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    # 向量存储：通过 pgvector extension 的 vector(N) 类型
    # embedding 列在 migration 中定义为 vector(1536)
    # 使用旧式 Column() 避免 Mapped[] 注解对 list[float] 类型推断失败
    embedding = Column(_VECTOR_TYPE, nullable=True)

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
