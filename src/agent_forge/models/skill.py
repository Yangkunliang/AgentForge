"""Skill 模型"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .agent_skill import AgentSkill
    from .task_execution import TaskExecution


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID str

    name: Mapped[str] = mapped_column(String(100), unique=True)
    version: Mapped[str] = mapped_column(String(20))  # Semantic Versioning
    description: Mapped[str] = mapped_column(Text)
    entry_point: Mapped[str] = mapped_column(String(255))  # e.g. "code_review.main"
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    installed_at: Mapped[str] = mapped_column(nullable=True)  # ISO datetime string

    # Relationships
    agent_skills: Mapped[list["AgentSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    executions: Mapped[list["TaskExecution"]] = relationship(back_populates="skill")

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name} v{self.version}>"
