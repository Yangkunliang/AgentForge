"""Skill 安装任务模型"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class SkillInstall(Base, TimestampMixin):
    __tablename__ = "skill_installs"

    id: Mapped[str] = mapped_column(primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(500))
    version: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    log: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<SkillInstall id={self.id} skill={self.skill_name} status={self.status}>"