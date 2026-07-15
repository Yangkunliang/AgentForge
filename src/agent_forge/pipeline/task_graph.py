"""TaskGraph structured output contract and validation."""

from __future__ import annotations

import json
import uuid
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_forge.models import (
    Artifact,
    PipelineRun,
    PipelineStageState,
    TaskGraph,
    TaskNode,
    TaskNodeDependency,
)

TASK_GRAPH_OUTPUT_CONTRACT_KEY = "task_graph_v1"


class TaskGraphOutputError(ValueError):
    """Raised when task_split output cannot form a safe TaskGraph."""


class TaskGraphAlreadyExistsError(ValueError):
    """Raised when a PipelineRun already owns a TaskGraph."""


class TaskNodeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_-]*$")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    depends_on: list[str] = Field(default_factory=list, max_length=20)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=20)
    target_files: list[str] = Field(default_factory=list, max_length=50)
    verification_commands: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("depends_on", "acceptance_criteria", "target_files", "verification_commands")
    @classmethod
    def _validate_unique_non_empty_items(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("list items must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("list items must be unique")
        return normalized

    @field_validator("target_files")
    @classmethod
    def _validate_target_files(cls, values: list[str]) -> list[str]:
        for value in values:
            path = PurePosixPath(value)
            if (
                path.is_absolute()
                or "\\" in value
                or ":" in value
                or any(part in {"", ".", ".."} for part in path.parts)
            ):
                raise ValueError("target files must be project-relative POSIX paths")
        return values


class TaskGraphSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str = Field(min_length=1, max_length=2000)
    nodes: list[TaskNodeSpec] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _validate_dag(self) -> TaskGraphSpec:
        node_by_key = {node.key: node for node in self.nodes}
        if len(node_by_key) != len(self.nodes):
            raise ValueError("duplicate node key")

        for node in self.nodes:
            for dependency in node.depends_on:
                if dependency == node.key:
                    raise ValueError(f"node {node.key} cannot depend on itself")
                if dependency not in node_by_key:
                    raise ValueError(
                        f"node {node.key} has unknown dependency {dependency}"
                    )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_key: str) -> None:
            if node_key in visiting:
                raise ValueError("task graph contains a dependency cycle")
            if node_key in visited:
                return
            visiting.add(node_key)
            for dependency in node_by_key[node_key].depends_on:
                visit(dependency)
            visiting.remove(node_key)
            visited.add(node_key)

        for node in self.nodes:
            visit(node.key)
        return self


def parse_task_graph_output(raw_output: str) -> TaskGraphSpec:
    """Parse strict raw JSON output into a validated TaskGraph spec."""
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise TaskGraphOutputError("task_graph_v1 output must be valid JSON") from exc
    try:
        return TaskGraphSpec.model_validate(payload)
    except ValidationError as exc:
        raise TaskGraphOutputError(str(exc)) from exc


async def create_task_graph(
    db: AsyncSession,
    *,
    run: PipelineRun,
    stage: PipelineStageState,
    source_artifact: Artifact,
    spec: TaskGraphSpec,
) -> TaskGraph:
    """Persist a validated graph and its dependency edges in the caller transaction."""
    existing = await db.scalar(
        select(TaskGraph.id).where(TaskGraph.pipeline_run_id == run.id)
    )
    if existing is not None:
        raise TaskGraphAlreadyExistsError(
            f"PipelineRun already has a TaskGraph: {run.id}"
        )

    graph = TaskGraph(
        id=str(uuid.uuid4()),
        project_id=run.project_id,
        pipeline_run_id=run.id,
        source_stage_state_id=stage.id,
        source_artifact_id=source_artifact.id,
        schema_version=1,
        status="ready",
        summary=spec.summary,
    )
    db.add(graph)

    node_by_key: dict[str, TaskNode] = {}
    for order_index, node_spec in enumerate(spec.nodes):
        node = TaskNode(
            id=str(uuid.uuid4()),
            task_graph=graph,
            node_key=node_spec.key,
            title=node_spec.title,
            description=node_spec.description,
            order_index=order_index,
            status="pending",
            acceptance_criteria=list(node_spec.acceptance_criteria),
            target_files=list(node_spec.target_files),
            verification_commands=list(node_spec.verification_commands),
        )
        db.add(node)
        node_by_key[node_spec.key] = node

    for node_spec in spec.nodes:
        node = node_by_key[node_spec.key]
        for dependency_key in node_spec.depends_on:
            db.add(
                TaskNodeDependency(
                    task_node=node,
                    dependency_node=node_by_key[dependency_key],
                )
            )

    await db.flush()
    return graph


async def load_task_graph_for_run(
    db: AsyncSession,
    *,
    run_id: str,
) -> TaskGraph | None:
    result = await db.execute(
        select(TaskGraph)
        .where(TaskGraph.pipeline_run_id == run_id)
        .options(
            selectinload(TaskGraph.nodes)
            .selectinload(TaskNode.dependencies)
            .selectinload(TaskNodeDependency.dependency_node)
        )
    )
    return result.unique().scalar_one_or_none()


def task_graph_to_dict(graph: TaskGraph) -> dict:
    return {
        "id": graph.id,
        "project_id": graph.project_id,
        "pipeline_run_id": graph.pipeline_run_id,
        "source_stage_state_id": graph.source_stage_state_id,
        "source_artifact_id": graph.source_artifact_id,
        "schema_version": graph.schema_version,
        "status": graph.status,
        "summary": graph.summary,
        "created_at": graph.created_at,
        "updated_at": graph.updated_at,
        "nodes": [
            {
                "id": node.id,
                "key": node.node_key,
                "title": node.title,
                "description": node.description,
                "order_index": node.order_index,
                "status": node.status,
                "depends_on": sorted(
                    dependency.dependency_node.node_key
                    for dependency in node.dependencies
                ),
                "acceptance_criteria": list(node.acceptance_criteria or []),
                "target_files": list(node.target_files or []),
                "verification_commands": list(node.verification_commands or []),
                "created_at": node.created_at,
                "updated_at": node.updated_at,
            }
            for node in graph.nodes
        ],
    }


def render_task_graph_markdown(spec: TaskGraphSpec) -> str:
    """Render a human-readable Artifact without losing the structured graph."""
    lines = [f"# 任务图：{spec.summary}", ""]
    for index, node in enumerate(spec.nodes, start=1):
        lines.extend(
            [
                f"## {index}. {node.title}",
                "",
                node.description,
                "",
                f"- 节点：`{node.key}`",
                f"- 依赖：{', '.join(node.depends_on) if node.depends_on else '无'}",
                f"- 目标文件：{', '.join(node.target_files) if node.target_files else '待执行阶段确定'}",
                "- 验收标准：",
            ]
        )
        lines.extend(f"  - {criterion}" for criterion in node.acceptance_criteria)
        lines.append("- 验证命令：")
        if node.verification_commands:
            lines.extend(f"  - `{command}`" for command in node.verification_commands)
        else:
            lines.append("  - 待 VerificationGate 确定")
        lines.append("")
    return "\n".join(lines).strip()


def get_output_contract_prompt(output_contract_key: str) -> str | None:
    if output_contract_key != TASK_GRAPH_OUTPUT_CONTRACT_KEY:
        return None
    return """- 结构化输出契约：task_graph_v1
  只输出原始 JSON，不要输出 Markdown fence、解释或前后缀文本。
  JSON 顶层字段："summary" 和 "nodes"。
  每个 node 必须包含："key"、"title"、"description"、"depends_on"、
  "acceptance_criteria"、"target_files"、"verification_commands"。
  depends_on 使用同一图中的 node key；图必须无环；target_files 必须是项目相对路径。"""
