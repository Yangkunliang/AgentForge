"""技能安装任务表 (SkillInstall)

记录每次技能安装/更新任务的执行过程和结果。
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class SkillInstall(Base, TimestampMixin):
    """技能安装任务表 — 记录每次技能安装/更新任务的执行过程和结果。

    当用户或系统请求安装/更新一个 Skill 时,生成一条记录跟踪安装进度、
    日志和错误信息。
    """
    __tablename__ = "skill_installs"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键

    skill_name: Mapped[str] = mapped_column(String(100))  # 被安装的技能名称

    source: Mapped[str] = mapped_column(String(500))  # 来源地址(GitHub URL / PyPI 包名 / 本地路径)

    version: Mapped[str] = mapped_column(String(20))  # 目标版本号

    status: Mapped[str] = mapped_column(String(20), default="pending")  # 安装状态: pending/processing/success/failed

    log: Mapped[str] = mapped_column(Text, default="")  # 安装过程日志

    error: Mapped[str | None] = mapped_column(Text)  # 错误信息(成功时为 None 或空)

    def __repr__(self) -> str:
        return f"<SkillInstall id={self.id} skill={self.skill_name} status={self.status}>"
