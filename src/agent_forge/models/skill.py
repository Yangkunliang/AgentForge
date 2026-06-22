"""Skill 模型"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .agent_skill import AgentSkill
    from .task_execution import TaskExecution


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(100), unique=True)
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    entry_point: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    installed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # 新增字段（Migration 002）
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="builtin"
    )  # builtin | local | github | pypi | clawhub
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    agent_skills: Mapped[list["AgentSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    executions: Mapped[list["TaskExecution"]] = relationship(back_populates="skill")

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name} v{self.version} enabled={self.enabled}>"
