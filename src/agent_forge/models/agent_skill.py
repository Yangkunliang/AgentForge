"""Agent-Skill 关联模型"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .agent import Agent
from .skill import Skill


class AgentSkill(Base):
    __tablename__ = "agent_skills"
    __table_args__ = {"extend_existing": True}

    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    # 是否在该 Agent 上启用此 Skill（Migration 002 新增）
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="agent_skills")
    skill = relationship("Skill", back_populates="agent_skills")

    def __repr__(self) -> str:
        return f"<AgentSkill agent={self.agent_id} skill={self.skill_id} enabled={self.enabled}>"
