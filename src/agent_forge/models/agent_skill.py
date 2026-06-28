"""Agent-Skill 关联表 (AgentSkill)

多对多关系表,连接 Agent 和 Skill,表示某个 Agent 被赋予了哪些技能。
enabled 字段控制该技能在当前 Agent 实例上是否启用。
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AgentSkill(Base):
    """Agent-Skill 关联表 — 多对多中间表,绑定 Agent 与 Skill。

    每个记录表示「某个 Agent 拥有某个 Skill」,enabled 字段控制
    该技能在此 Agent 实例上是否处于启用状态。
    """
    __tablename__ = "agent_skills"
    __table_args__ = ({"extend_existing": True},)

    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )  # 主键第一部分,所属 Agent ID

    skill_id: Mapped[str] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )  # 主键第二部分,所属 Skill ID

    # 是否在该 Agent 上启用此 Skill(Migration 002 新增)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # 技能启用标志

    # Relationships
    agent = relationship("Agent", back_populates="agent_skills")
    skill = relationship("Skill", back_populates="agent_skills")

    def __repr__(self) -> str:
        return f"<AgentSkill agent={self.agent_id} skill={self.skill_id} enabled={self.enabled}>"
