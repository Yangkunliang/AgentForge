"""Session 和 Message 模型（面向用户的对话会话）"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class Session(Base, TimestampMixin):
    """用户对话会话，类比 ChatGPT 的一条侧边栏记录"""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(100), default="新对话")

    # Relationships
    user = relationship("User")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} title={self.title!r}>"


class Message(Base, TimestampMixin):
    """会话内的单条消息（user 或 assistant）"""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)

    # 关联到后端执行的 Task（仅 user 消息触发，assistant 消息为 None）
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )

    # 执行过程数据：thinking / tool_call / code_execution 步骤，JSON 列存储
    # 列名用 extra_data 避开 SQLAlchemy 保留属性名 metadata
    extra_data: list | None = Column("extra_data", JSONB, nullable=True, default=None)

    # Relationships
    session = relationship("Session", back_populates="messages")
    task = relationship("Task")

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role} session={self.session_id}>"
