"""用户表 (User)

存储平台注册用户的基本信息、登录凭据和资料。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:

    from .api_key import APIKey
    from .task import Task


class User(Base, TimestampMixin):
    """用户表 — 存储平台注册用户的基本信息、登录凭据和个人资料。

    关联关系:
        tasks: 该用户创建的所有任务
        api_keys: 该用户创建的 API Key
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # 唯一用户名,用于登录
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # 邮箱地址,用于登录和通知
    password_hash: Mapped[str] = mapped_column(String(255))  # bcrypt/argon2 密码哈希值

    permissions: Mapped[dict] = mapped_column(JSON, default=list)  # 用户权限配置

    # 个人资料
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)  # 显示昵称
    avatar_url: Mapped[str | None] = mapped_column(String(524288), nullable=True, default=None)  # 头像 URL 或 base64 data URL,最大 512 KB

    # Relationships
    tasks: Mapped[list[Task]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[Task.user_id]",
    )
    api_keys: Mapped[list[APIKey]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"
