"""技能定义表 (Skill)

存储平台所有技能的定义信息,包括技能元数据、来源类型、依赖关系和启用状态。
技能是 Agent 可调用的具体能力单元(如代码执行、文件搜索等)。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .agent_skill import AgentSkill
    from .task_execution import TaskExecution


class Skill(Base, TimestampMixin):
    """技能定义表 — 存储所有技能的元数据和配置。

    每个技能是一个可复用的能力单元,可以被多个 Agent 绑定使用。
    支持多种来源类型:builtin(内置)、local(本地)、github、pypi、clawhub。

    关联关系:
        agent_skills: 绑定此技能的所有 Agent(多对多中间表)
        executions: 通过此技能执行过的任务记录
    """
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键,UUID 字符串

    name: Mapped[str] = mapped_column(String(100), unique=True)  # 技能唯一名称
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 版本号
    description: Mapped[str] = mapped_column(Text)  # 功能描述
    entry_point: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 执行器入口(模块:函数名)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)  # 技能完整配置清单
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)  # 依赖的 Python 包名列表
    installed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 安装时间

    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )  # 创建者用户 ID

    # 新增字段(Migration 002)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # 是否启用此技能
    source_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="builtin"
    )  # 来源: builtin / local / github / pypi / clawhub
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 图标 URL
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)  # 标签列表
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # GitHub 仓库地址

    # Relationships
    agent_skills: Mapped[list[AgentSkill]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    executions: Mapped[list[TaskExecution]] = relationship(back_populates="skill")

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name} v{self.version} enabled={self.enabled}>"
