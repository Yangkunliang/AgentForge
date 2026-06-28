"""API Key 表 (APIKey)

存储用户的 API 访问密钥。密钥以 SHA256 哈希形式存储,不保存明文。
用于 API 认证和权限控制。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:

    pass


class APIKey(Base, TimestampMixin):
    """API Key 表 — 存储用户的服务端访问密钥。

    密钥以 SHA256 哈希形式存储,不保存明文。用户通过 API 请求时携带此密钥,
    服务端计算哈希值进行认证。

    关联关系:
        user: 所属用户
    """
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))  # 所属用户 ID

    key_hash: Mapped[str] = mapped_column(String(255))  # SHA256 哈希值,不存明文

    name: Mapped[str] = mapped_column(String(100))  # Key 名称(用户自定义,便于管理)

    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)  # 此 Key 的权限列表

    active: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否激活(可停用)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} name={self.name}>"
