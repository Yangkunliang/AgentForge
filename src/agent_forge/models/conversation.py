"""Conversation 模型"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum as sa_Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .task import Task


from enum import Enum as PyEnum


class MessageType(str, PyEnum):
    BID = "bid"
    MESSAGE = "message"
    RESULT = "result"


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    from_agent: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"))
    to_agent: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )  # NULL = broadcast
    message_type: Mapped[str] = mapped_column(sa_Enum(MessageType), default=MessageType.MESSAGE)
    content: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    task = relationship("Task", back_populates="conversations")

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} type={self.message_type.value}>"
