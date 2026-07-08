"""会话与消息模型(面向用户的对话记录)

Session — 用户的对话会话(侧边栏中的一条记录),对应后端一个 Task 的执行上下文。
Message — 会话内的单条消息,记录用户输入、AI 回复及执行过程数据。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, JSON_VARIANT, TimestampMixin

if TYPE_CHECKING:
    from .pipeline import PipelineRun
    from .project import Artifact, Project


class Session(Base, TimestampMixin):
    """用户对话会话 — 类比 ChatGPT 侧边栏中的一条记录。

    每个 Session 代表用户的一次对话(一次完整的需求交互上下文),
    关联一个后端 Task(任务执行记录)。

    关联关系:
        user: 创建此会话的用户
        messages: 按时间排序的会话内所有消息
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # 主键,固定 50 字符

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)  # 所属用户 ID
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # 所属项目 ID,旧会话允许为空

    title: Mapped[str] = mapped_column(String(100), default="新对话")  # 会话标题
    intent_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    current_pipeline_run_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    user = relationship("User")
    project: Mapped[Project | None] = relationship("Project", back_populates="sessions")
    messages: Mapped[list[Message]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    pipeline_runs: Mapped[list[PipelineRun]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PipelineRun.created_at",
    )
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="session")

    def __repr__(self) -> str:
        return f"<Session id={self.id} title={self.title!r}>"


class Message(Base, TimestampMixin):
    """会话消息 — 记录单条用户输入或 AI 回复,以及执行过程数据。

    每条 Message 代表对话中的一行消息:
    - user 角色:用户发来的需求/指令,会触发后端 Task 执行
    - assistant 角色:AI 返回的回答/结果

    extra_data 列以 JSONB 格式存储执行过程中的结构化数据(thinking steps、
    tool_call 记录、code_execution 输出),用于前端展示执行明细。
    """

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # 主键

    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )  # 所属会话 ID

    role: Mapped[str] = mapped_column(String(20))  # 消息角色: "user" 或 "assistant"
    content: Mapped[str] = mapped_column(Text)  # 消息正文

    # 关联到后端执行的 Task(仅 user 消息触发,assistant 消息为 None)
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )  # 触发的任务 ID

    # 执行过程数据:thinking / tool_call / code_execution 步骤,JSONB 列存储
    # 列名用 extra_data 避开 SQLAlchemy 保留属性名 metadata
    extra_data: list | None = Column("extra_data", JSON_VARIANT, nullable=True, default=None)  # 执行步骤明细

    # Relationships
    session = relationship("Session", back_populates="messages")
    task = relationship("Task")

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role} session={self.session_id}>"
