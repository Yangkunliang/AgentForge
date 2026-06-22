"""用户 AI 助手设置模型"""

from __future__ import annotations

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class UserAgentSettings(Base, TimestampMixin):
    """每个用户的 AI 助手个性化设置"""

    __tablename__ = "user_agent_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), default="CodeSoul")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
