"""Authorized WorkspaceChangeSet preview and read APIs."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import get_async_session
from agent_forge.governance import GovernancePolicy
from agent_forge.models import AuditLog, User
from agent_forge.tracing import get_trace_id
from agent_forge.workspace import (
    FileProposal,
    WorkspaceExecutionError,
    apply_workspace_change_set,
    create_workspace_preview,
    load_workspace_change_set_for_user,
    workspace_change_set_to_dict,
)
from middleware.auth import get_current_user

task_graph_router = APIRouter()
router = APIRouter()


class FileProposalRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=2000)
    content: str = Field(..., max_length=200000)


class WorkspacePreviewRequest(BaseModel):
    mount_id: str = Field(..., min_length=1, max_length=50)
    source_artifact_id: str | None = Field(default=None, max_length=50)
    files: list[FileProposalRequest] = Field(..., min_length=1, max_length=50)


class WorkspaceApplyRequest(BaseModel):
    confirm_write: bool = False


class BaseFingerprintResponse(BaseModel):
    exists: bool
    size: int
    sha256: str | None


class FilePatchResponse(BaseModel):
    id: str
    target_path: str
    operation: str
    status: str
    has_changes: bool
    unified_diff: str
    base_fingerprint: BaseFingerprintResponse
    created_at: datetime
    updated_at: datetime


class WorkspaceChangeSetResponse(BaseModel):
    id: str
    project_id: str
    task_graph_id: str
    task_node_id: str
    mount_id: str
    source_artifact_id: str | None
    status: str
    has_changes: bool
    apply_report: dict | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    patches: list[FilePatchResponse]


@task_graph_router.post(
    "/{graph_id}/nodes/{node_key}/workspace/preview",
    response_model=WorkspaceChangeSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def preview_workspace_change_set(
    graph_id: str,
    node_key: str,
    body: WorkspacePreviewRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        change_set = await create_workspace_preview(
            db,
            user_id=current_user.id,
            graph_id=graph_id,
            node_key=node_key,
            mount_id=body.mount_id,
            source_artifact_id=body.source_artifact_id,
            proposals=[
                FileProposal(path=item.path, content=item.content)
                for item in body.files
            ],
        )
    except WorkspaceExecutionError as exc:
        _add_workspace_audit(
            db,
            action="workspace.preview.failed",
            status_value="failed",
            user_id=current_user.id,
            change_set_id=None,
            graph_id=graph_id,
            node_key=node_key,
            mount_id=body.mount_id,
            details={"error_code": exc.error_code, "error_message": exc.detail},
        )
        await db.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    payload = workspace_change_set_to_dict(change_set)
    _add_workspace_audit(
        db,
        action="workspace.preview.succeeded",
        status_value="success",
        user_id=current_user.id,
        change_set_id=change_set.id,
        graph_id=graph_id,
        node_key=node_key,
        mount_id=body.mount_id,
        details={
            "file_count": len(change_set.patches),
            "changed_count": sum(patch.has_changes for patch in change_set.patches),
            "target_paths": [patch.target_path for patch in change_set.patches],
        },
    )
    await db.commit()
    return payload


@router.get("/{change_set_id}", response_model=WorkspaceChangeSetResponse)
async def get_workspace_change_set(
    change_set_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        change_set = await load_workspace_change_set_for_user(
            db,
            change_set_id=change_set_id,
            user_id=current_user.id,
        )
    except WorkspaceExecutionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return workspace_change_set_to_dict(change_set)


@router.post("/{change_set_id}/apply", response_model=WorkspaceChangeSetResponse)
async def apply_workspace_change_set_api(
    change_set_id: str,
    body: WorkspaceApplyRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        change_set = await load_workspace_change_set_for_user(
            db,
            change_set_id=change_set_id,
            user_id=current_user.id,
            for_update=True,
        )
    except WorkspaceExecutionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    governance = GovernancePolicy().evaluate_workspace_confirmation(
        change_set_id=change_set.id,
        mount_id=change_set.mount_id,
        target_paths=[patch.target_path for patch in change_set.patches],
        confirmed=body.confirm_write,
    )
    if not governance.allowed:
        _add_workspace_audit(
            db,
            action="workspace.apply.denied",
            status_value="denied",
            user_id=current_user.id,
            change_set_id=change_set.id,
            graph_id=change_set.task_graph_id,
            node_key=change_set.task_node.node_key,
            mount_id=change_set.mount_id,
            details={
                "reason": "missing_confirmation",
                "governance_decision": governance.audit_payload(),
                "target_paths": [patch.target_path for patch in change_set.patches],
            },
        )
        await db.commit()
        raise HTTPException(
            status_code=409,
            detail="Write confirmation is required before workspace apply",
        )

    was_applied = change_set.status == "applied"
    try:
        change_set = await apply_workspace_change_set(db, change_set=change_set)
    except WorkspaceExecutionError as exc:
        action = (
            "workspace.apply.conflict"
            if exc.error_code == "baseline_changed"
            else "workspace.apply.failed"
        )
        _add_workspace_audit(
            db,
            action=action,
            status_value="failed",
            user_id=current_user.id,
            change_set_id=change_set.id,
            graph_id=change_set.task_graph_id,
            node_key=change_set.task_node.node_key,
            mount_id=change_set.mount_id,
            details={
                "error_code": exc.error_code,
                "error_message": exc.detail,
                "report": exc.report,
            },
        )
        await db.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    report = change_set.apply_report_json or {}
    _add_workspace_audit(
        db,
        action=(
            "workspace.apply.idempotent"
            if was_applied
            else "workspace.apply.succeeded"
        ),
        status_value="success",
        user_id=current_user.id,
        change_set_id=change_set.id,
        graph_id=change_set.task_graph_id,
        node_key=change_set.task_node.node_key,
        mount_id=change_set.mount_id,
        details={
            "file_count": report.get("file_count", 0),
            "changed_count": report.get("changed_count", 0),
            "total_bytes_written": report.get("total_bytes_written", 0),
            "target_paths": [patch.target_path for patch in change_set.patches],
            "governance_decision": governance.audit_payload(),
        },
    )
    await db.commit()
    return workspace_change_set_to_dict(change_set)


def _add_workspace_audit(
    db: AsyncSession,
    *,
    action: str,
    status_value: str,
    user_id: str,
    change_set_id: str | None,
    graph_id: str,
    node_key: str,
    mount_id: str,
    details: dict,
) -> None:
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            action=action,
            resource="workspace_change_set",
            user_id=user_id,
            trace_id=get_trace_id() or str(uuid.uuid4()),
            status=status_value,
            degraded=False,
            details={
                "change_set_id": change_set_id,
                "task_graph_id": graph_id,
                "task_node_key": node_key,
                "mount_id": mount_id,
                **details,
            },
        )
    )
