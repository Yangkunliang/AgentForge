"""Project-first development workflow models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, JSON_VARIANT, TimestampMixin

if TYPE_CHECKING:
    from .pipeline import PipelineRun
    from .session import Session


class Project(Base, TimestampMixin):
    """用户授权给 AgentForge 使用的项目容器。"""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_tags: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)

    user = relationship("User", back_populates="projects")
    mounts: Mapped[list[ProjectMount]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMount.created_at",
    )
    sessions: Mapped[list[Session]] = relationship(back_populates="project")
    pipeline_runs: Mapped[list[PipelineRun]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="PipelineRun.created_at",
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Artifact.created_at",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"


class ProjectMount(Base, TimestampMixin):
    """Project 下用户主动授权的代码库或文件入口。"""

    __tablename__ = "project_mounts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    mount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="primary")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    metadata_json: dict = Column("metadata", JSON_VARIANT, nullable=True, default=dict)

    project = relationship("Project", back_populates="mounts")

    def __repr__(self) -> str:
        return f"<ProjectMount id={self.id} type={self.mount_type} project={self.project_id}>"


class Artifact(Base, TimestampMixin):
    """阶段产物归档，先存数据库内容，后续可迁移对象存储。"""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    pipeline_run_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    stage_state_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: dict = Column("metadata", JSON_VARIANT, nullable=True, default=dict)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    delivery_target_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_report_json: dict | None = Column("delivery_report", JSON_VARIANT, nullable=True)

    project = relationship("Project", back_populates="artifacts")
    session = relationship("Session", back_populates="artifacts")

    def __repr__(self) -> str:
        return f"<Artifact id={self.id} type={self.artifact_type} project={self.project_id}>"
