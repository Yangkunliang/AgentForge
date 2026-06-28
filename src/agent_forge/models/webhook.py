"""Webhook 表 (Webhook)

存储用户配置的 Webhook 端点,用于在事件发生时(如任务完成)
向外部系统发送 HTTP 回调通知。
"""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Webhook(Base, TimestampMixin):
    """Webhook 表 — 存储用户配置的 Webhook 回调端点。

    当平台中触发指定事件(如任务完成)时,向配置的 URL 发送 HTTP POST 通知。
    secret_key 用于签名验证,events 指定监听的事件类型。
    """
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键

    user_id: Mapped[str] = mapped_column(String(64))  # 所属用户 ID

    url: Mapped[str] = mapped_column(String(500))  # 回调 URL

    events: Mapped[list] = mapped_column(JSON, default=list)  # 监听的事件类型列表

    secret_key: Mapped[str] = mapped_column(String(64))  # 签名密钥,用于验证请求来源

    is_active: Mapped[bool] = mapped_column(default=True)  # 是否激活

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 描述

    def __repr__(self) -> str:
        return f"<Webhook id={self.id} url={self.url}>"
