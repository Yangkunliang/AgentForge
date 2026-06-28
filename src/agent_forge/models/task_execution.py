"""任务执行记录表 (TaskExecution)

记录每次 Agent 对 Task 或 SubTask 的具体执行过程,包括输入输出、Token 消耗、成本、耗时等。
用于成本追踪、性能分析和调试。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:

    pass


class ExecutionStatus(str):
    SUCCESS = "success"
    FAILED = "failed"


class TaskExecution(Base, TimestampMixin):
    """任务执行记录 — 记录每次 Agent 执行任务的具体过程数据。

    每次 Executor 调用一个 Agent(使用某个 Skill)执行 Task 或 SubTask 时,
    都会生成一条记录,包含输入、输出、Token 消耗、成本、耗时等。

    Fields:
        task_id: 关联的父任务
        sub_task_id: 关联的子任务(如有)
        agent_id: 执行该任务的 Agent
        skill_id: 使用的 Skill(如有)
        input_data: 输入参数
        output: 输出结果
        tokens_used: Token 用量统计
        cost_usd: 本次执行成本(美元)
        duration_ms: 执行耗时(毫秒)
        model_used: 使用的 LLM 模型
        status: 执行状态 (success/failed)
        user_feedback: 用户反馈

    Relationships:
        task: 关联的父任务
        agent: 执行 Agent
        skill: 使用的技能
    """
    __tablename__ = "task_executions"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))  # 所属父任务 ID

    sub_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("sub_tasks.id", ondelete="SET NULL"), nullable=True
    )  # 所属子任务 ID(顶级任务为 None)

    agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )  # 执行此任务的 Agent ID

    skill_id: Mapped[str | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )  # 使用的 Skill ID(如有)

    input_data: Mapped[dict] = mapped_column(JSON, default=dict)  # 输入参数

    output: Mapped[dict] = mapped_column(JSON, default=dict)  # 输出结果

    tokens_used: Mapped[dict] = mapped_column(JSON, default=dict)  # Token 用量统计

    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)  # 本次执行成本(美元)

    duration_ms: Mapped[int] = mapped_column(Integer, default=0)  # 执行耗时(毫秒)

    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 使用的 LLM 模型名

    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.SUCCESS)  # 执行状态: "success" / "failed"

    user_feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)  # 用户反馈

    # Relationships
    task = relationship("Task", back_populates="executions")
    agent = relationship("Agent", back_populates="executions")
    skill = relationship("Skill", back_populates="executions")

    def __repr__(self) -> str:
        return f"<TaskExecution id={self.id} status={self.status}>"
