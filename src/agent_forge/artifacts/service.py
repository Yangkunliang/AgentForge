"""Artifact creation helpers for stage outputs."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Artifact, PipelineRun, PipelineStageState

ARTIFACT_TYPES = {"prd", "architecture", "api_spec", "code", "test", "report", "diff"}

_STAGE_ARTIFACT_TYPE: dict[str, str] = {
    "analysis": "prd",
    "design": "architecture",
    "db_api": "api_spec",
    "task_split": "report",
    "ui_prototype": "prd",
    "backend_dev": "code",
    "frontend_dev": "code",
    "testing": "test",
    "diff": "diff",
    "impact": "report",
    "regression": "test",
    "prototype_diff": "diff",
    "visual": "report",
    "locate": "report",
    "impact_scope": "report",
    "fix": "code",
}


def infer_stage_artifact_type(stage_id: str) -> str:
    """Map pipeline stage ids to product-level artifact types."""
    return _STAGE_ARTIFACT_TYPE.get(stage_id, "report")


async def create_stage_artifact(
    db: AsyncSession,
    *,
    run: PipelineRun,
    stage: PipelineStageState,
    task_id: str,
    content: str,
    source_message_id: str | None = None,
    runtime_metadata: dict | None = None,
) -> Artifact:
    """Persist the completed stage output as an Artifact."""
    normalized_content = content.strip() or "阶段未产生文本输出。"
    artifact_type = infer_stage_artifact_type(stage.stage_id)
    metadata = {
        "intent_type": run.intent_type,
        "stage_id": stage.stage_id,
        "stage_name": stage.stage_name,
        "stage_order": stage.order_index,
        "task_id": task_id,
        "origin": "stage_runtime",
    }
    if runtime_metadata:
        metadata["runtime"] = runtime_metadata

    artifact = Artifact(
        id=str(uuid.uuid4()),
        project_id=run.project_id,
        session_id=run.session_id,
        pipeline_run_id=run.id,
        stage_state_id=stage.id,
        artifact_type=artifact_type,
        name=f"{stage.stage_name}.md",
        content=normalized_content,
        file_type="markdown",
        source_message_id=source_message_id,
        metadata_json=metadata,
    )
    db.add(artifact)
    await db.flush()
    return artifact


def build_stage_runtime_metadata(
    stage: PipelineStageState,
    *,
    skill_policy_key: str | None = None,
) -> dict:
    """Build non-sensitive provenance for artifacts created by StageRuntime."""
    return {
        "agent_profile": {
            "id": stage.agent_profile_id,
            "name": stage.agent_profile_name,
            "source": stage.agent_profile_source,
        },
        "model_route": {
            "route_key": stage.model_route_key,
            "name": stage.model_route_name,
            "source": stage.model_route_source,
        },
        "model_name": stage.model_name,
        "skill_policy_key": skill_policy_key or "default",
    }
