"""Authorized workspace change set and file patch models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import JSON_VARIANT, Base, TimestampMixin

if TYPE_CHECKING:
    from .project import Artifact, ProjectMount
    from .task_graph import TaskGraph, TaskNode


class WorkspaceChangeSet(Base, TimestampMixin):
    __tablename__ = "workspace_change_sets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_graph_id: Mapped[str] = mapped_column(
        ForeignKey("task_graphs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_node_id: Mapped[str] = mapped_column(
        ForeignKey("task_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mount_id: Mapped[str] = mapped_column(
        ForeignKey("project_mounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mount_root_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="previewed",
        index=True,
    )
    apply_report_json: Mapped[dict | None] = mapped_column(
        "apply_report",
        JSON_VARIANT,
        nullable=True,
    )
    applied_at: Mapped[datetime | None] = mapped_column(nullable=True)

    task_graph: Mapped[TaskGraph] = relationship("TaskGraph")
    task_node: Mapped[TaskNode] = relationship("TaskNode")
    mount: Mapped[ProjectMount] = relationship("ProjectMount")
    source_artifact: Mapped[Artifact | None] = relationship("Artifact")
    patches: Mapped[list[FilePatch]] = relationship(
        back_populates="change_set",
        cascade="all, delete-orphan",
        order_by="FilePatch.target_path",
    )


class FilePatch(Base, TimestampMixin):
    __tablename__ = "file_patches"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    change_set_id: Mapped[str] = mapped_column(
        ForeignKey("workspace_change_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False, default="upsert")
    proposed_content: Mapped[str] = mapped_column(Text, nullable=False)
    unified_diff: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_exists: Mapped[bool] = mapped_column(Boolean, nullable=False)
    base_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_changes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="previewed",
        index=True,
    )

    change_set: Mapped[WorkspaceChangeSet] = relationship(
        "WorkspaceChangeSet",
        back_populates="patches",
    )

    __table_args__ = (
        UniqueConstraint(
            "change_set_id",
            "target_path",
            name="uq_file_patches_change_set_path",
        ),
    )
