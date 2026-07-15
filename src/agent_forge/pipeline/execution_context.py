"""Typed execution context for a Pipeline stage."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Artifact, PipelineRun, PipelineStageState
from agent_forge.pipeline.catalog import StageDefinition

DEFAULT_MAX_ARTIFACTS = 6
DEFAULT_MAX_ARTIFACT_CONTENT_CHARS = 4000
DEFAULT_MAX_TOTAL_CONTENT_CHARS = 12000


@dataclass(frozen=True)
class UpstreamArtifactContext:
    artifact_id: str
    stage_id: str
    stage_name: str
    stage_order: int
    artifact_type: str
    name: str
    content: str
    content_truncated: bool

    def to_context(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "stage_order": self.stage_order,
            "artifact_type": self.artifact_type,
            "name": self.name,
            "content": self.content,
            "content_truncated": self.content_truncated,
        }


@dataclass(frozen=True)
class StageExecutionContext:
    project_id: str
    session_id: str
    pipeline_run_id: str
    intent_type: str
    stage_id: str
    stage_name: str
    stage_order: int
    description: str
    required_input_artifact_types: tuple[str, ...]
    expected_output_artifact_types: tuple[str, ...]
    output_contract_key: str | None
    success_criteria: tuple[str, ...]
    missing_input_artifact_types: tuple[str, ...]
    upstream_artifacts: tuple[UpstreamArtifactContext, ...]

    def to_context(self) -> dict:
        payload = {
            "project_id": self.project_id,
            "session_id": self.session_id,
            "pipeline_run_id": self.pipeline_run_id,
            "intent_type": self.intent_type,
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "stage_order": self.stage_order,
            "description": self.description,
            "required_input_artifact_types": list(self.required_input_artifact_types),
            "expected_output_artifact_types": list(self.expected_output_artifact_types),
            "success_criteria": list(self.success_criteria),
            "missing_input_artifact_types": list(self.missing_input_artifact_types),
            "upstream_artifacts": [item.to_context() for item in self.upstream_artifacts],
        }
        if self.output_contract_key:
            payload["output_contract_key"] = self.output_contract_key
        return payload


async def build_stage_execution_context(
    db: AsyncSession,
    *,
    run: PipelineRun,
    stage: PipelineStageState,
    stage_definition: StageDefinition,
    max_artifacts: int = DEFAULT_MAX_ARTIFACTS,
    max_artifact_content_chars: int = DEFAULT_MAX_ARTIFACT_CONTENT_CHARS,
    max_total_content_chars: int = DEFAULT_MAX_TOTAL_CONTENT_CHARS,
) -> StageExecutionContext:
    """Build a bounded context using only artifacts from earlier stages in this run."""
    artifacts = await _load_run_artifacts(db, run)
    stage_by_state_id = {item.id: item for item in run.stages}
    required_types = stage_definition.required_input_artifact_types

    latest_candidates: dict[
        tuple[str, str],
        tuple[PipelineStageState, Artifact],
    ] = {}
    for artifact in artifacts:
        source_stage = stage_by_state_id.get(artifact.stage_state_id)
        if source_stage is None or source_stage.order_index >= stage.order_index:
            continue
        if required_types and artifact.artifact_type not in required_types:
            continue
        revision_key = (source_stage.id, artifact.artifact_type)
        existing = latest_candidates.get(revision_key)
        if existing is None or _artifact_revision_key(artifact) > _artifact_revision_key(
            existing[1]
        ):
            latest_candidates[revision_key] = (source_stage, artifact)

    candidates = sorted(
        latest_candidates.values(),
        key=lambda item: (item[0].order_index, item[1].artifact_type, item[1].id),
    )
    upstream_artifacts = _build_upstream_artifacts(
        candidates,
        max_artifacts=max_artifacts,
        max_artifact_content_chars=max_artifact_content_chars,
        max_total_content_chars=max_total_content_chars,
    )
    available_types = {artifact.artifact_type for artifact in upstream_artifacts}
    missing_types = tuple(
        artifact_type
        for artifact_type in required_types
        if artifact_type not in available_types
    )
    return StageExecutionContext(
        project_id=run.project_id,
        session_id=run.session_id,
        pipeline_run_id=run.id,
        intent_type=run.intent_type,
        stage_id=stage.stage_id,
        stage_name=stage.stage_name,
        stage_order=stage.order_index,
        description=stage_definition.description,
        required_input_artifact_types=required_types,
        expected_output_artifact_types=stage_definition.output_artifact_types,
        output_contract_key=stage_definition.output_contract_key,
        success_criteria=stage_definition.success_criteria,
        missing_input_artifact_types=missing_types,
        upstream_artifacts=upstream_artifacts,
    )


async def _load_run_artifacts(db: AsyncSession, run: PipelineRun) -> list[Artifact]:
    result = await db.execute(
        select(Artifact)
        .where(
            Artifact.project_id == run.project_id,
            Artifact.pipeline_run_id == run.id,
        )
        .order_by(Artifact.created_at.asc(), Artifact.id.asc())
    )
    return list(result.scalars().all())


def _artifact_revision_key(artifact: Artifact) -> tuple:
    return artifact.created_at, artifact.id


def _build_upstream_artifacts(
    candidates: list[tuple[PipelineStageState, Artifact]],
    *,
    max_artifacts: int,
    max_artifact_content_chars: int,
    max_total_content_chars: int,
) -> tuple[UpstreamArtifactContext, ...]:
    item_limit = max(0, max_artifacts)
    content_limit = max(0, max_artifact_content_chars)
    remaining_chars = max(0, max_total_content_chars)
    result: list[UpstreamArtifactContext] = []
    selected_candidates = candidates[:item_limit]

    for index, (source_stage, artifact) in enumerate(selected_candidates):
        if remaining_chars <= 0:
            break
        remaining_items = len(selected_candidates) - index
        fair_share = remaining_chars // remaining_items
        allowed_chars = min(content_limit, fair_share)
        if allowed_chars <= 0:
            break
        content = artifact.content[:allowed_chars]
        result.append(
            UpstreamArtifactContext(
                artifact_id=artifact.id,
                stage_id=source_stage.stage_id,
                stage_name=source_stage.stage_name,
                stage_order=source_stage.order_index,
                artifact_type=artifact.artifact_type,
                name=artifact.name,
                content=content,
                content_truncated=len(content) < len(artifact.content),
            )
        )
        remaining_chars -= len(content)

    return tuple(result)
