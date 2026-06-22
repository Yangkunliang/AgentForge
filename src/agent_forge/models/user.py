"""User 模型"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .api_key import APIKey
    from .task import Task


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    permissions: Mapped[dict] = mapped_column(JSON, default=list)

    # 个人资料
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(524288), nullable=True, default=None)  # base64 data URL，最大 512 KB

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[Task.user_id]",
    )
    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"
