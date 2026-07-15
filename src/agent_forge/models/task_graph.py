"""Structured Pipeline TaskGraph models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import JSON_VARIANT, Base, TimestampMixin

if TYPE_CHECKING:
    from .pipeline import PipelineRun, PipelineStageState
    from .project import Artifact


class TaskGraph(Base, TimestampMixin):
    __tablename__ = "task_graphs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_run_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_stage_state_id: Mapped[str | None] = mapped_column(
        ForeignKey("pipeline_stage_states.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ready", index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    pipeline_run: Mapped[PipelineRun] = relationship(
        "PipelineRun",
        back_populates="task_graph",
    )
    source_stage: Mapped[PipelineStageState | None] = relationship(
        "PipelineStageState",
        foreign_keys=[source_stage_state_id],
    )
    source_artifact: Mapped[Artifact | None] = relationship(
        "Artifact",
        foreign_keys=[source_artifact_id],
    )
    nodes: Mapped[list[TaskNode]] = relationship(
        back_populates="task_graph",
        cascade="all, delete-orphan",
        order_by="TaskNode.order_index",
    )

    __table_args__ = (
        UniqueConstraint("pipeline_run_id", name="uq_task_graphs_pipeline_run_id"),
    )


class TaskNode(Base, TimestampMixin):
    __tablename__ = "task_nodes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    task_graph_id: Mapped[str] = mapped_column(
        ForeignKey("task_graphs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    acceptance_criteria: Mapped[list[str]] = mapped_column(
        JSON_VARIANT,
        nullable=False,
        default=list,
    )
    target_files: Mapped[list[str]] = mapped_column(
        JSON_VARIANT,
        nullable=False,
        default=list,
    )
    verification_commands: Mapped[list[str]] = mapped_column(
        JSON_VARIANT,
        nullable=False,
        default=list,
    )

    task_graph: Mapped[TaskGraph] = relationship("TaskGraph", back_populates="nodes")
    dependencies: Mapped[list[TaskNodeDependency]] = relationship(
        "TaskNodeDependency",
        back_populates="task_node",
        cascade="all, delete-orphan",
        foreign_keys="TaskNodeDependency.task_node_id",
    )

    __table_args__ = (
        UniqueConstraint("task_graph_id", "node_key", name="uq_task_nodes_graph_key"),
        UniqueConstraint("task_graph_id", "order_index", name="uq_task_nodes_graph_order"),
    )


class TaskNodeDependency(Base):
    __tablename__ = "task_node_dependencies"

    task_node_id: Mapped[str] = mapped_column(
        ForeignKey("task_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    depends_on_node_id: Mapped[str] = mapped_column(
        ForeignKey("task_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )

    task_node: Mapped[TaskNode] = relationship(
        "TaskNode",
        back_populates="dependencies",
        foreign_keys=[task_node_id],
    )
    dependency_node: Mapped[TaskNode] = relationship(
        "TaskNode",
        foreign_keys=[depends_on_node_id],
    )
