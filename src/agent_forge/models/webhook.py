"""Webhook 模型"""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Webhook(Base, TimestampMixin):
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(String(500))
    events: Mapped[list] = mapped_column(JSON, default=list)
    secret_key: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Webhook id={self.id} url={self.url}>"
