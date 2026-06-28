"""Agent 间对话表 (Conversation)

存储 Agent 协商过程中(Contract Net 协议)产生的消息。
包括招标(bid)、消息传递(message)和结果上报(result)。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey
from sqlalchemy import Enum as sa_Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:

    pass


from enum import StrEnum


class MessageType(StrEnum):
    """消息类型枚举 — 定义 Agent 间对话的消息种类。

    - BID: 招标消息(Contract Net 协议中 Agent 竞标)
    - MESSAGE: 普通消息传递
    - RESULT: 结果上报
    """

    BID = "bid"
    MESSAGE = "message"
    RESULT = "result"


class Conversation(Base, TimestampMixin):
    """Agent 间对话表 — 存储 Agent 协商过程中的消息记录。

    用于 Contract Net 协议中的 Agent 间通信,包括招标、消息传递和结果上报。
    所有消息归属于一个 Task,支持点对点(指定 to_agent)和广播(to_agent=None)。

    关联关系:
        task: 所属的父任务
    """
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))  # 所属任务 ID

    from_agent: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"))  # 发送方 Agent ID

    to_agent: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )  # 接收方 Agent ID(None = 广播给所有 Agent)

    message_type: Mapped[str] = mapped_column(sa_Enum(MessageType), default=MessageType.MESSAGE)  # 消息类型

    content: Mapped[dict] = mapped_column(JSON, default=dict)  # 消息内容(JSON)

    # Relationships
    task = relationship("Task", back_populates="conversations")

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} type={self.message_type.value}>"
