"""用户 AI 助手个性化设置表 (UserAgentSettings)

存储每个用户对 AI 助手的自定义配置,如助手名称、头像等。
每个用户只有一条记录(user_id 唯一约束)。
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class UserAgentSettings(Base, TimestampMixin):
    """用户 AI 助手个性化设置 — 每个用户的 AI 助手定制配置。

    支持自定义助手名称和头像,让用户在平台中获得个性化的 AI 助手体验。
    每个用户只有一条记录。
    """

    __tablename__ = "user_agent_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # 主键

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )  # 所属用户 ID(唯一)

    agent_name: Mapped[str] = mapped_column(String(100), default="CodeSoul")  # 助手名称

    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 助手头像 URL
