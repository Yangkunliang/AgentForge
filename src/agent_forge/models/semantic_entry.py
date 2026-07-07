"""语义记忆条目模型(pgvector 向量存储)"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, JSON_VARIANT

# pgvector 可选依赖:PostgreSQL 使用 vector,SQLite 测试环境降级为 JSON
try:
    from pgvector.sqlalchemy import Vector as _Vector
    _VECTOR_TYPE = JSON().with_variant(_Vector(1536), "postgresql")
except ImportError:
    _VECTOR_TYPE = JSON()


class SemanticEntry(Base):
    """语义记忆条目 — 跨会话语义记忆,支持向量相似度检索

    embedding 列在 Alembic migration 中创建为 vector(N) 类型(pgvector extension)。
    运行时通过 pgvector.sqlalchemy.Vector 类型绑定。
    """

    __tablename__ = "semantic_entries"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )  # 所属用户 ID

    task_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )  # 关联的任务 ID(可选)

    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")  # 记忆标题

    content: Mapped[str] = mapped_column(Text, nullable=False)  # 记忆内容

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        # decision, code, design, result, context, preference
    )  # 分类

    extra_data: Mapped[dict] = mapped_column("metadata", JSON_VARIANT, nullable=False, default=dict)  # 额外数据(映射为 DB 列名 metadata)

    # 向量存储:通过 pgvector extension 的 vector(N) 类型
    # embedding 列在 migration 中定义为 vector(1536)
    # 使用旧式 Column() 避免 Mapped[] 注解对 list[float] 类型推断失败
    embedding = Column(_VECTOR_TYPE, nullable=True)  # 向量嵌入(1536 维)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 版本号(支持内容更新)

    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # 软删除标记

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
        # 复合索引
        Index("ix_semantic_user_category", "user_id", "category"),
        Index("ix_semantic_deleted", "deleted"),
    )

    def __repr__(self) -> str:
        return f"<SemanticEntry(id={self.id}, category={self.category})>"
