"""Project, mount, project session and artifact routes."""

from __future__ import annotations

import secrets
import urllib.parse
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.bridge.files import BridgeAccessError, list_mount_files, read_mount_file, root_path_for_mount
from agent_forge.config import settings
from agent_forge.database import get_async_session
from agent_forge.delivery import (
    DeliveryConsistencyError,
    apply_artifact_delivery,
    build_delivery_report_markdown,
    mark_artifact_delivery_failed,
    preview_artifact_delivery,
)
from agent_forge.integrations.github import (
    GitHubOAuthError,
    build_github_authorization_url,
    exchange_github_oauth_code,
    fetch_github_repo,
)
from agent_forge.models import Artifact, AuditLog, OAuthCredential, OAuthState, Project, ProjectMount, User
from agent_forge.models.session import Session
from agent_forge.security.credentials import encrypt_secret
from agent_forge.tracing import get_trace_id
from middleware.auth import get_current_user

router = APIRouter()
artifact_router = APIRouter()

IntentType = Literal["new_feature", "iteration", "ui_adjust", "bug_fix"]
MountType = Literal["local", "github", "upload"]
MountRole = Literal["primary", "reference", "docs"]
MountStatus = Literal["connected", "disconnected", "pending", "error"]
ArtifactType = Literal["prd", "architecture", "api_spec", "code", "test", "report", "diff"]


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    tech_tags: list[str] = Field(default_factory=list, max_length=20)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    tech_tags: list[str] | None = Field(default=None, max_length=20)
    status: Literal["active", "archived"] | None = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    display_name: str
    description: str | None
    tech_tags: list[str]
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectSessionCreateRequest(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=100)
    intent_type: IntentType | None = None


class ProjectSessionResponse(BaseModel):
    id: str
    project_id: str | None
    title: str
    intent_type: str | None
    current_pipeline_run_id: str | None
    created_at: datetime
    updated_at: datetime


class MountCreateRequest(BaseModel):
    mount_type: MountType
    display_name: str = Field(..., min_length=1, max_length=120)
    locator: str = Field(..., min_length=1, max_length=4000)
    role: MountRole = "primary"
    status: MountStatus = "pending"
    metadata: dict = Field(default_factory=dict)


class MountUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    locator: str | None = Field(default=None, min_length=1, max_length=4000)
    role: MountRole | None = None
    status: MountStatus | None = None
    metadata: dict | None = None


class GitHubOAuthStartRequest(BaseModel):
    repo_full_name: str = Field(..., min_length=3, max_length=200)
    role: MountRole = "primary"
    redirect_uri: str | None = Field(default=None, max_length=4000)


class GitHubOAuthStartResponse(BaseModel):
    authorization_url: str
    state: str
    expires_at: datetime


class MountResponse(BaseModel):
    id: str
    project_id: str
    mount_type: str
    display_name: str
    locator: str
    role: str
    status: str
    metadata: dict
    created_at: datetime
    updated_at: datetime


class BridgeStatusMountResponse(BaseModel):
    mount_id: str
    mount_type: str
    display_name: str
    role: str
    status: str
    root_path: str | None


class BridgeStatusResponse(BaseModel):
    project_id: str
    connected_mounts: int
    mounts: list[BridgeStatusMountResponse]


class MountFileEntryResponse(BaseModel):
    name: str
    relative_path: str
    kind: Literal["file", "directory"]
    size: int | None
    modified_at: datetime


class MountFileListResponse(BaseModel):
    mount_id: str
    project_id: str
    path: str
    entries: list[MountFileEntryResponse]


class MountFileReadRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=2000)


class MountFileReadResponse(BaseModel):
    mount_id: str
    project_id: str
    path: str
    content: str
    size: int
    truncated: bool


class ArtifactCreateRequest(BaseModel):
    session_id: str | None = None
    pipeline_run_id: str | None = None
    stage_state_id: str | None = None
    artifact_type: ArtifactType
    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    file_type: str | None = Field(default=None, max_length=40)
    source_message_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class ArtifactUpdateRequest(BaseModel):
    artifact_type: ArtifactType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    file_type: str | None = Field(default=None, max_length=40)
    metadata: dict | None = None


class ArtifactResponse(BaseModel):
    id: str
    project_id: str
    session_id: str | None
    pipeline_run_id: str | None
    stage_state_id: str | None
    artifact_type: str
    name: str
    content: str
    file_type: str | None
    source_message_id: str | None
    metadata: dict
    delivery_status: str
    delivery_target_path: str | None
    delivered_at: datetime | None
    delivery_report: dict | None
    created_at: datetime
    updated_at: datetime


class DeliveryPreviewRequest(BaseModel):
    mount_id: str = Field(..., min_length=1, max_length=50)
    target_path: str = Field(..., min_length=1, max_length=2000)


class DeliveryApplyRequest(DeliveryPreviewRequest):
    confirm_write: bool = False
    expected_target_hash: str | None = Field(default=None, max_length=64)


class DeliveryResponse(BaseModel):
    artifact_id: str
    project_id: str
    mount_id: str
    target_path: str
    status: Literal["previewed", "delivered", "failed"]
    has_changes: bool
    unified_diff: str
    report: dict


def _clean_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for tag in tags:
        value = tag.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value[:40])
    return cleaned


def _project_to_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "user_id": project.user_id,
        "name": project.name,
        "display_name": project.name,
        "description": project.description,
        "tech_tags": project.tech_tags or [],
        "status": project.status,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def _session_to_dict(session: Session) -> dict:
    return {
        "id": session.id,
        "project_id": session.project_id,
        "title": session.title,
        "intent_type": session.intent_type,
        "current_pipeline_run_id": session.current_pipeline_run_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def _mount_to_dict(mount: ProjectMount) -> dict:
    return {
        "id": mount.id,
        "project_id": mount.project_id,
        "mount_type": mount.mount_type,
        "display_name": mount.display_name,
        "locator": mount.locator,
        "role": mount.role,
        "status": mount.status,
        "metadata": mount.metadata_json or {},
        "created_at": mount.created_at,
        "updated_at": mount.updated_at,
    }


def _parse_repo_full_name(repo_full_name: str) -> tuple[str, str]:
    value = repo_full_name.strip()
    parts = value.split("/")
    if (
        len(parts) != 2
        or not parts[0]
        or not parts[1]
        or any(part in {".", ".."} for part in parts)
        or any("\\" in part for part in parts)
    ):
        raise HTTPException(status_code=400, detail="GitHub repo must use owner/name format")
    return parts[0], parts[1]


def _artifact_to_dict(artifact: Artifact) -> dict:
    return {
        "id": artifact.id,
        "project_id": artifact.project_id,
        "session_id": artifact.session_id,
        "pipeline_run_id": artifact.pipeline_run_id,
        "stage_state_id": artifact.stage_state_id,
        "artifact_type": artifact.artifact_type,
        "name": artifact.name,
        "content": artifact.content,
        "file_type": artifact.file_type,
        "source_message_id": artifact.source_message_id,
        "metadata": artifact.metadata_json or {},
        "delivery_status": artifact.delivery_status,
        "delivery_target_path": artifact.delivery_target_path,
        "delivered_at": artifact.delivered_at,
        "delivery_report": artifact.delivery_report_json,
        "created_at": artifact.created_at,
        "updated_at": artifact.updated_at,
    }


async def _get_project_or_404(db: AsyncSession, project_id: str, user_id: str) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.status != "archived",
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_project_session_or_404(
    db: AsyncSession,
    session_id: str,
    project_id: str,
    user_id: str,
) -> Session:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.project_id == project_id,
            Session.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _get_mount_or_404(
    db: AsyncSession,
    project_id: str,
    mount_id: str,
    user_id: str,
) -> ProjectMount:
    await _get_project_or_404(db, project_id, user_id)
    result = await db.execute(
        select(ProjectMount).where(
            ProjectMount.id == mount_id,
            ProjectMount.project_id == project_id,
        )
    )
    mount = result.scalar_one_or_none()
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")
    return mount


def _ensure_connected_local_mount(mount: ProjectMount) -> None:
    if mount.mount_type != "local":
        raise HTTPException(status_code=400, detail="Only local mounts support file access")
    if mount.status != "connected":
        raise HTTPException(status_code=409, detail="Mount is not connected")


def _raise_bridge_error(exc: BridgeAccessError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _add_delivery_audit(
    db: AsyncSession,
    *,
    action: str,
    status_value: str,
    user_id: str,
    artifact: Artifact,
    mount: ProjectMount,
    target_path: str,
    details: dict | None = None,
) -> None:
    payload = {
        "artifact_id": artifact.id,
        "project_id": artifact.project_id,
        "mount_id": mount.id,
        "target_path": target_path,
    }
    if details:
        payload.update(details)
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            action=action,
            resource="artifact_delivery",
            user_id=user_id,
            trace_id=get_trace_id() or artifact.id,
            status=status_value,
            degraded=False,
            details=payload,
        )
    )


def _add_github_mount_audit(
    db: AsyncSession,
    *,
    action: str,
    status_value: str,
    user_id: str,
    project_id: str,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            action=action,
            resource="github_mount",
            user_id=user_id,
            trace_id=get_trace_id() or project_id,
            status=status_value,
            degraded=False,
            details={"project_id": project_id, **(details or {})},
        )
    )


def _oauth_value(payload: object, key: str):
    if isinstance(payload, dict):
        return payload[key]
    return getattr(payload, key)


def _oauth_optional_value(payload: object, key: str, default=None):
    if isinstance(payload, dict):
        return payload.get(key, default)
    return getattr(payload, key, default)


def _is_expired(expires_at: datetime) -> bool:
    now = datetime.now(UTC)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now


def _github_redirect_uri(body_redirect_uri: str | None, project_id: str) -> str:
    redirect_uri = (body_redirect_uri or settings.github_oauth_redirect_uri).strip()
    if body_redirect_uri:
        parsed = urllib.parse.urlparse(redirect_uri)
        expected_path = f"/api/v1/projects/{project_id}/mounts/github/oauth/callback"
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path != expected_path:
            raise HTTPException(status_code=400, detail="GitHub OAuth redirect URI is not allowed")
    return redirect_uri


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id, Project.status != "archived")
        .order_by(Project.updated_at.desc())
    )
    return [_project_to_dict(project) for project in result.scalars().all()]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    project = Project(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=body.name.strip(),
        description=body.description.strip() if body.description else None,
        tech_tags=_clean_tags(body.tech_tags),
        status="active",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _project_to_dict(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    return _project_to_dict(await _get_project_or_404(db, project_id, current_user.id))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    project = await _get_project_or_404(db, project_id, current_user.id)
    if body.name is not None:
        project.name = body.name.strip()
    if body.description is not None:
        project.description = body.description.strip() or None
    if body.tech_tags is not None:
        project.tech_tags = _clean_tags(body.tech_tags)
    if body.status is not None:
        project.status = body.status
    await db.commit()
    await db.refresh(project)
    return _project_to_dict(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> None:
    project = await _get_project_or_404(db, project_id, current_user.id)
    project.status = "archived"
    await db.commit()


@router.post("/{project_id}/sessions", response_model=ProjectSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_project_session(
    project_id: str,
    body: ProjectSessionCreateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    project = await _get_project_or_404(db, project_id, current_user.id)
    session = Session(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        project_id=project.id,
        title=body.title.strip()[:100],
        intent_type=body.intent_type,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_to_dict(session)


@router.get("/{project_id}/sessions", response_model=list[ProjectSessionResponse])
async def list_project_sessions(
    project_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    await _get_project_or_404(db, project_id, current_user.id)
    result = await db.execute(
        select(Session)
        .where(Session.project_id == project_id, Session.user_id == current_user.id)
        .order_by(Session.updated_at.desc())
    )
    return [_session_to_dict(session) for session in result.scalars().all()]


@router.post(
    "/{project_id}/mounts/github/oauth/start",
    response_model=GitHubOAuthStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_github_oauth_mount(
    project_id: str,
    body: GitHubOAuthStartRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    project = await _get_project_or_404(db, project_id, current_user.id)
    owner, repo = _parse_repo_full_name(body.repo_full_name)
    redirect_uri = _github_redirect_uri(body.redirect_uri, project.id)
    if not settings.github_oauth_client_id or not redirect_uri:
        _add_github_mount_audit(
            db,
            action="github_mount.oauth.failed",
            status_value="failed",
            user_id=current_user.id,
            project_id=project.id,
            details={"repo_full_name": f"{owner}/{repo}", "error_code": "github_oauth_not_configured"},
        )
        await db.commit()
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    state_value = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    oauth_state = OAuthState(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        project_id=project.id,
        provider="github",
        state=state_value,
        redirect_uri=redirect_uri,
        expires_at=expires_at,
        metadata_json={
            "repo_full_name": f"{owner}/{repo}",
            "role": body.role,
        },
    )
    db.add(oauth_state)
    _add_github_mount_audit(
        db,
        action="github_mount.oauth.started",
        status_value="pending",
        user_id=current_user.id,
        project_id=project.id,
        details={"repo_full_name": f"{owner}/{repo}", "role": body.role},
    )
    await db.commit()
    return {
        "authorization_url": build_github_authorization_url(state=state_value, redirect_uri=redirect_uri),
        "state": state_value,
        "expires_at": expires_at,
    }


@router.get(
    "/{project_id}/mounts/github/oauth/callback",
    response_model=MountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def complete_github_oauth_mount(
    project_id: str,
    code: str = Query(..., min_length=1, max_length=500),
    state: str = Query(..., min_length=1, max_length=200),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    result = await db.execute(
        select(OAuthState).where(
            OAuthState.state == state,
            OAuthState.project_id == project_id,
            OAuthState.provider == "github",
            OAuthState.consumed_at.is_(None),
        )
    )
    oauth_state = result.scalar_one_or_none()
    if not oauth_state or _is_expired(oauth_state.expires_at):
        if oauth_state:
            _add_github_mount_audit(
                db,
                action="github_mount.oauth.failed",
                status_value="failed",
                user_id=oauth_state.user_id,
                project_id=project_id,
                details={"error_code": "invalid_or_expired_state"},
            )
            await db.commit()
        raise HTTPException(status_code=400, detail="OAuth state is invalid or expired")

    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == oauth_state.user_id,
            Project.status != "archived",
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        _add_github_mount_audit(
            db,
            action="github_mount.oauth.failed",
            status_value="failed",
            user_id=oauth_state.user_id,
            project_id=project_id,
            details={"error_code": "project_not_found"},
        )
        await db.commit()
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = oauth_state.metadata_json or {}
    repo_full_name = str(metadata.get("repo_full_name") or "")
    if not repo_full_name:
        raise HTTPException(status_code=400, detail="OAuth state is missing repo metadata")

    try:
        token = await exchange_github_oauth_code(code, oauth_state.redirect_uri)
        access_token = _oauth_value(token, "access_token")
        scopes = list(_oauth_optional_value(token, "scopes", []))
        repo_info = await fetch_github_repo(access_token, repo_full_name)
    except GitHubOAuthError as exc:
        _add_github_mount_audit(
            db,
            action="github_mount.oauth.failed",
            status_value="failed",
            user_id=oauth_state.user_id,
            project_id=project.id,
            details={"repo_full_name": repo_full_name, "error_code": "github_oauth_error", "error_message": str(exc)},
        )
        await db.commit()
        raise HTTPException(status_code=502, detail="GitHub OAuth callback failed") from exc

    credential = OAuthCredential(
        id=str(uuid.uuid4()),
        user_id=oauth_state.user_id,
        provider="github",
        name=f"GitHub {repo_info['full_name']}",
        encrypted_access_token=encrypt_secret(access_token),
        scopes_json=scopes,
        metadata_json={"repo_full_name": repo_info["full_name"]},
    )
    mount = ProjectMount(
        id=str(uuid.uuid4()),
        project_id=project.id,
        mount_type="github",
        display_name=repo_info["name"],
        locator=f"github://{repo_info['full_name']}",
        role=str(metadata.get("role") or "primary"),
        status="connected",
        metadata_json={
            "repo_owner": repo_info["owner"],
            "repo_name": repo_info["name"],
            "repo_full_name": repo_info["full_name"],
            "default_branch": repo_info["default_branch"],
            "html_url": repo_info["html_url"],
            "permission_summary": scopes,
            "credential_id": credential.id,
        },
    )
    oauth_state.consumed_at = datetime.now(UTC)
    db.add(credential)
    db.add(mount)
    _add_github_mount_audit(
        db,
        action="github_mount.oauth.succeeded",
        status_value="success",
        user_id=oauth_state.user_id,
        project_id=project.id,
        details={
            "repo_full_name": repo_info["full_name"],
            "mount_id": mount.id,
            "credential_id": credential.id,
            "scopes": scopes,
        },
    )
    await db.commit()
    await db.refresh(mount)
    return _mount_to_dict(mount)


@router.post("/{project_id}/mounts", response_model=MountResponse, status_code=status.HTTP_201_CREATED)
async def create_mount(
    project_id: str,
    body: MountCreateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    project = await _get_project_or_404(db, project_id, current_user.id)
    mount = ProjectMount(
        id=str(uuid.uuid4()),
        project_id=project.id,
        mount_type=body.mount_type,
        display_name=body.display_name.strip(),
        locator=body.locator.strip(),
        role=body.role,
        status=body.status,
        metadata_json=body.metadata,
    )
    db.add(mount)
    await db.commit()
    await db.refresh(mount)
    return _mount_to_dict(mount)


@router.get("/{project_id}/mounts", response_model=list[MountResponse])
async def list_mounts(
    project_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    await _get_project_or_404(db, project_id, current_user.id)
    result = await db.execute(
        select(ProjectMount)
        .where(ProjectMount.project_id == project_id)
        .order_by(ProjectMount.created_at.asc())
    )
    return [_mount_to_dict(mount) for mount in result.scalars().all()]


@router.get("/{project_id}/bridge/status", response_model=BridgeStatusResponse)
async def get_bridge_status(
    project_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await _get_project_or_404(db, project_id, current_user.id)
    result = await db.execute(
        select(ProjectMount)
        .where(ProjectMount.project_id == project_id)
        .order_by(ProjectMount.created_at.asc())
    )

    mounts: list[dict] = []
    connected_mounts = 0
    for mount in result.scalars().all():
        root_path: str | None = None
        bridge_status = mount.status
        if mount.mount_type == "local" and mount.status == "connected":
            try:
                root_path = str(root_path_for_mount(mount))
                connected_mounts += 1
            except BridgeAccessError:
                bridge_status = "error"

        mounts.append(
            {
                "mount_id": mount.id,
                "mount_type": mount.mount_type,
                "display_name": mount.display_name,
                "role": mount.role,
                "status": bridge_status,
                "root_path": root_path,
            }
        )

    return {
        "project_id": project_id,
        "connected_mounts": connected_mounts,
        "mounts": mounts,
    }


@router.get("/{project_id}/mounts/{mount_id}/files", response_model=MountFileListResponse)
async def list_mount_file_entries(
    project_id: str,
    mount_id: str,
    path: str = Query(default="", max_length=2000),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    mount = await _get_mount_or_404(db, project_id, mount_id, current_user.id)
    _ensure_connected_local_mount(mount)
    try:
        return list_mount_files(mount, path)
    except BridgeAccessError as exc:
        _raise_bridge_error(exc)


@router.post("/{project_id}/mounts/{mount_id}/files/read", response_model=MountFileReadResponse)
async def read_mount_file_content(
    project_id: str,
    mount_id: str,
    body: MountFileReadRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    mount = await _get_mount_or_404(db, project_id, mount_id, current_user.id)
    _ensure_connected_local_mount(mount)
    try:
        return read_mount_file(mount, body.path)
    except BridgeAccessError as exc:
        _raise_bridge_error(exc)


@router.patch("/{project_id}/mounts/{mount_id}", response_model=MountResponse)
async def update_mount(
    project_id: str,
    mount_id: str,
    body: MountUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await _get_project_or_404(db, project_id, current_user.id)
    result = await db.execute(
        select(ProjectMount).where(ProjectMount.id == mount_id, ProjectMount.project_id == project_id)
    )
    mount = result.scalar_one_or_none()
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")
    if body.display_name is not None:
        mount.display_name = body.display_name.strip()
    if body.locator is not None:
        mount.locator = body.locator.strip()
    if body.role is not None:
        mount.role = body.role
    if body.status is not None:
        mount.status = body.status
    if body.metadata is not None:
        mount.metadata_json = body.metadata
    await db.commit()
    await db.refresh(mount)
    return _mount_to_dict(mount)


@router.delete("/{project_id}/mounts/{mount_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mount(
    project_id: str,
    mount_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> None:
    await _get_project_or_404(db, project_id, current_user.id)
    result = await db.execute(
        select(ProjectMount).where(ProjectMount.id == mount_id, ProjectMount.project_id == project_id)
    )
    mount = result.scalar_one_or_none()
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")
    if mount.mount_type == "github":
        credential_id = (mount.metadata_json or {}).get("credential_id")
        if credential_id:
            credential_result = await db.execute(
                select(OAuthCredential).where(
                    OAuthCredential.id == credential_id,
                    OAuthCredential.user_id == current_user.id,
                    OAuthCredential.provider == "github",
                )
            )
            credential = credential_result.scalar_one_or_none()
            if credential:
                credential.revoked_at = datetime.now(UTC)
        _add_github_mount_audit(
            db,
            action="github_mount.revoked",
            status_value="success",
            user_id=current_user.id,
            project_id=project_id,
            details={"mount_id": mount.id, "credential_id": credential_id},
        )
    await db.delete(mount)
    await db.commit()


@router.post("/{project_id}/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    project_id: str,
    body: ArtifactCreateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    project = await _get_project_or_404(db, project_id, current_user.id)
    if body.session_id is not None:
        await _get_project_session_or_404(db, body.session_id, project.id, current_user.id)

    artifact = Artifact(
        id=str(uuid.uuid4()),
        project_id=project.id,
        session_id=body.session_id,
        pipeline_run_id=body.pipeline_run_id,
        stage_state_id=body.stage_state_id,
        artifact_type=body.artifact_type,
        name=body.name.strip(),
        content=body.content,
        file_type=body.file_type,
        source_message_id=body.source_message_id,
        metadata_json=body.metadata,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return _artifact_to_dict(artifact)


@router.get("/{project_id}/artifacts", response_model=list[ArtifactResponse])
async def list_project_artifacts(
    project_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    await _get_project_or_404(db, project_id, current_user.id)
    result = await db.execute(
        select(Artifact)
        .where(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
    )
    return [_artifact_to_dict(artifact) for artifact in result.scalars().all()]


async def _get_artifact_or_404(db: AsyncSession, artifact_id: str, user_id: str) -> Artifact:
    result = await db.execute(
        select(Artifact)
        .join(Project, Artifact.project_id == Project.id)
        .where(
            Artifact.id == artifact_id,
            Project.user_id == user_id,
            Project.status != "archived",
        )
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


async def _get_delivery_mount_or_404(
    db: AsyncSession,
    artifact: Artifact,
    mount_id: str,
    user_id: str,
) -> ProjectMount:
    mount = await _get_mount_or_404(db, artifact.project_id, mount_id, user_id)
    _ensure_connected_local_mount(mount)
    return mount


@artifact_router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    return _artifact_to_dict(await _get_artifact_or_404(db, artifact_id, current_user.id))


@artifact_router.post("/{artifact_id}/delivery/preview", response_model=DeliveryResponse)
async def preview_artifact_delivery_api(
    artifact_id: str,
    body: DeliveryPreviewRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    artifact = await _get_artifact_or_404(db, artifact_id, current_user.id)
    mount = await _get_delivery_mount_or_404(db, artifact, body.mount_id, current_user.id)
    try:
        delivery = preview_artifact_delivery(artifact, mount, body.target_path)
    except BridgeAccessError as exc:
        _add_delivery_audit(
            db,
            action="delivery.preview.failed",
            status_value="failed",
            user_id=current_user.id,
            artifact=artifact,
            mount=mount,
            target_path=body.target_path,
            details={"error_code": "bridge_access_error", "error_message": exc.detail},
        )
        await db.commit()
        _raise_bridge_error(exc)
    _add_delivery_audit(
        db,
        action="delivery.preview.succeeded",
        status_value="success",
        user_id=current_user.id,
        artifact=artifact,
        mount=mount,
        target_path=delivery["target_path"],
        details={
            "has_changes": delivery["has_changes"],
            "target_fingerprint": delivery["report"].get("target_fingerprint"),
        },
    )
    await db.commit()
    return delivery


@artifact_router.post("/{artifact_id}/delivery/apply", response_model=DeliveryResponse)
async def apply_artifact_delivery_api(
    artifact_id: str,
    body: DeliveryApplyRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    artifact = await _get_artifact_or_404(db, artifact_id, current_user.id)
    mount = await _get_delivery_mount_or_404(db, artifact, body.mount_id, current_user.id)
    if not body.confirm_write:
        _add_delivery_audit(
            db,
            action="delivery.apply.denied",
            status_value="denied",
            user_id=current_user.id,
            artifact=artifact,
            mount=mount,
            target_path=body.target_path,
            details={"reason": "missing_confirmation"},
        )
        await db.commit()
        raise HTTPException(status_code=409, detail="Write confirmation is required before delivery")

    try:
        delivery = await apply_artifact_delivery(
            db,
            artifact,
            mount,
            body.target_path,
            expected_target_hash=body.expected_target_hash,
        )
    except DeliveryConsistencyError as exc:
        _add_delivery_audit(
            db,
            action="delivery.apply.conflict",
            status_value="failed",
            user_id=current_user.id,
            artifact=artifact,
            mount=mount,
            target_path=body.target_path,
            details=exc.report,
        )
        await db.commit()
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    except BridgeAccessError as exc:
        report = await mark_artifact_delivery_failed(
            db,
            artifact,
            mount,
            body.target_path,
            phase="apply",
            error_code="bridge_access_error",
            error_message=exc.detail,
            recovery_hint="Review the target path, mount status, and sensitive file policy before retrying.",
        )
        _add_delivery_audit(
            db,
            action="delivery.apply.failed",
            status_value="failed",
            user_id=current_user.id,
            artifact=artifact,
            mount=mount,
            target_path=body.target_path,
            details=report,
        )
        await db.commit()
        _raise_bridge_error(exc)
    except Exception as exc:
        report = await mark_artifact_delivery_failed(
            db,
            artifact,
            mount,
            body.target_path,
            phase="apply",
            error_code="unexpected_error",
            error_message=str(exc) or exc.__class__.__name__,
            recovery_hint="Retry after checking server logs. If the error repeats, keep the backup and inspect the mount path.",
        )
        _add_delivery_audit(
            db,
            action="delivery.apply.failed",
            status_value="failed",
            user_id=current_user.id,
            artifact=artifact,
            mount=mount,
            target_path=body.target_path,
            details=report,
        )
        await db.commit()
        raise HTTPException(status_code=500, detail="Delivery failed unexpectedly") from exc
    _add_delivery_audit(
        db,
        action="delivery.apply.succeeded",
        status_value="success",
        user_id=current_user.id,
        artifact=artifact,
        mount=mount,
        target_path=delivery["target_path"],
        details={
            "backup_path": delivery["report"].get("backup_path"),
            "bytes_written": delivery["report"].get("bytes_written"),
            "target_fingerprint": delivery["report"].get("target_fingerprint"),
            "expected_target_hash": body.expected_target_hash,
        },
    )
    await db.commit()
    await db.refresh(artifact)
    return delivery


@artifact_router.get("/{artifact_id}/delivery/report")
async def get_artifact_delivery_report(
    artifact_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    artifact = await _get_artifact_or_404(db, artifact_id, current_user.id)
    if artifact.delivery_status != "delivered" or not artifact.delivery_report_json:
        raise HTTPException(status_code=409, detail="Artifact has not been delivered")

    filename = f"{artifact.name}.delivery.md".replace('"', "")
    return Response(
        content=build_delivery_report_markdown(artifact),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@artifact_router.patch("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    artifact_id: str,
    body: ArtifactUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    artifact = await _get_artifact_or_404(db, artifact_id, current_user.id)
    if body.artifact_type is not None:
        artifact.artifact_type = body.artifact_type
    if body.name is not None:
        artifact.name = body.name.strip()
    if body.content is not None:
        artifact.content = body.content
    if body.file_type is not None:
        artifact.file_type = body.file_type
    if body.metadata is not None:
        artifact.metadata_json = body.metadata
    await db.commit()
    await db.refresh(artifact)
    return _artifact_to_dict(artifact)


@artifact_router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> None:
    artifact = await _get_artifact_or_404(db, artifact_id, current_user.id)
    await db.delete(artifact)
    await db.commit()
