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
) -> Artifact:
    """Persist the completed stage output as an Artifact."""
    normalized_content = content.strip() or "阶段未产生文本输出。"
    artifact_type = infer_stage_artifact_type(stage.stage_id)
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
        metadata_json={
            "intent_type": run.intent_type,
            "stage_id": stage.stage_id,
            "stage_name": stage.stage_name,
            "stage_order": stage.order_index,
            "task_id": task_id,
            "origin": "stage_runtime",
        },
    )
    db.add(artifact)
    await db.flush()
    return artifact
