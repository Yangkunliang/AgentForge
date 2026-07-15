"""Preview file-level changes inside an authorized ProjectMount."""

from __future__ import annotations

import difflib
import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_forge.bridge.files import (
    MAX_FILE_BYTES,
    BridgeAccessError,
    normalize_mount_relative_path,
    read_mount_file,
    restore_mount_file,
    root_path_for_mount,
    write_mount_file,
)
from agent_forge.models import (
    Artifact,
    FilePatch,
    Project,
    ProjectMount,
    TaskGraph,
    TaskNode,
    WorkspaceChangeSet,
)

MAX_PATCH_FILES = 50
MAX_PATCH_FILE_BYTES = MAX_FILE_BYTES
MAX_PATCH_TOTAL_BYTES = 2_000_000


@dataclass(frozen=True, slots=True)
class FileProposal:
    path: str
    content: str


@dataclass(frozen=True, slots=True)
class _PreparedPatch:
    proposal: FileProposal
    fingerprint: dict
    has_changes: bool
    unified_diff: str


class WorkspaceExecutionError(Exception):
    """HTTP-friendly workspace validation or execution error."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        report: dict | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        self.report = report or {}


async def create_workspace_preview(
    db: AsyncSession,
    *,
    user_id: str,
    graph_id: str,
    node_key: str,
    mount_id: str,
    proposals: list[FileProposal],
    source_artifact_id: str | None = None,
) -> WorkspaceChangeSet:
    """Validate and persist a multi-file preview without writing the mount."""
    graph, node = await _load_task_node_for_user(db, graph_id, node_key, user_id)
    mount = await _load_workspace_mount(db, graph.project_id, mount_id, user_id)
    if source_artifact_id is not None:
        await _validate_source_artifact(
            db,
            project_id=graph.project_id,
            artifact_id=source_artifact_id,
            user_id=user_id,
        )
    normalized = _normalize_proposals(node, mount, proposals)

    prepared_patches: list[_PreparedPatch] = []
    for proposal in normalized:
        old_content, fingerprint = _read_baseline(mount, proposal.path)
        prepared_patches.append(
            _PreparedPatch(
                proposal=proposal,
                fingerprint=fingerprint,
                has_changes=(
                    not fingerprint["exists"] or old_content != proposal.content
                ),
                unified_diff=_unified_diff(
                    old_content,
                    proposal.content,
                    proposal.path,
                    base_exists=fingerprint["exists"],
                ),
            )
        )

    change_set = WorkspaceChangeSet(
        id=str(uuid.uuid4()),
        project_id=graph.project_id,
        task_graph_id=graph.id,
        task_node_id=node.id,
        mount_id=mount.id,
        mount_root_sha256=_mount_root_sha256(mount),
        source_artifact_id=source_artifact_id,
        status="previewed",
    )
    db.add(change_set)

    for prepared in prepared_patches:
        proposal = prepared.proposal
        fingerprint = prepared.fingerprint
        patch = FilePatch(
            id=str(uuid.uuid4()),
            change_set=change_set,
            target_path=proposal.path,
            operation="upsert",
            proposed_content=proposal.content,
            unified_diff=prepared.unified_diff,
            base_exists=fingerprint["exists"],
            base_sha256=fingerprint["sha256"],
            base_size=fingerprint["size"],
            has_changes=prepared.has_changes,
            status="previewed",
        )
        db.add(patch)

    await db.flush()
    return change_set


async def load_workspace_change_set_for_user(
    db: AsyncSession,
    *,
    change_set_id: str,
    user_id: str,
    for_update: bool = False,
) -> WorkspaceChangeSet:
    statement = (
        select(WorkspaceChangeSet)
        .join(Project, WorkspaceChangeSet.project_id == Project.id)
        .where(
            WorkspaceChangeSet.id == change_set_id,
            Project.user_id == user_id,
        )
        .options(
            selectinload(WorkspaceChangeSet.patches),
            selectinload(WorkspaceChangeSet.mount),
            selectinload(WorkspaceChangeSet.task_node),
        )
    )
    if for_update:
        statement = statement.with_for_update(of=WorkspaceChangeSet)
    result = await db.execute(statement)
    change_set = result.unique().scalar_one_or_none()
    if change_set is None:
        raise WorkspaceExecutionError(
            404,
            "WorkspaceChangeSet not found",
            "change_set_not_found",
        )
    return change_set


async def apply_workspace_change_set(
    db: AsyncSession,
    *,
    change_set: WorkspaceChangeSet,
) -> WorkspaceChangeSet:
    """Apply a confirmed preview with full preflight and normal-failure rollback."""
    if change_set.status == "applied":
        return change_set
    if change_set.status == "failed":
        raise WorkspaceExecutionError(
            409,
            "Failed WorkspaceChangeSet must be previewed again",
            "change_set_failed",
            change_set.apply_report_json,
        )
    if change_set.status != "previewed":
        raise WorkspaceExecutionError(
            409,
            f"WorkspaceChangeSet cannot be applied from status {change_set.status}",
            "change_set_not_ready",
            change_set.apply_report_json,
        )

    _validate_apply_scope(change_set)

    patches = sorted(change_set.patches, key=lambda patch: patch.target_path)
    mount = change_set.mount
    originals: dict[str, str | None] = {}
    conflicts: list[dict] = []
    for patch in patches:
        content, fingerprint = _read_baseline(mount, patch.target_path)
        originals[patch.target_path] = content if fingerprint["exists"] else None
        if not _baseline_matches(patch, fingerprint):
            conflicts.append(
                {
                    "path": patch.target_path,
                    "expected": _patch_fingerprint(patch),
                    "actual": fingerprint,
                }
            )

    started_at = datetime.now(UTC)
    if conflicts:
        conflict_paths = {item["path"] for item in conflicts}
        for patch in patches:
            patch.status = "conflict" if patch.target_path in conflict_paths else "not_applied"
        report = {
            "status": "failed",
            "phase": "consistency_check",
            "error_code": "baseline_changed",
            "error_message": "Workspace target changed since preview",
            "conflicts": conflicts,
            "rollback": {
                "attempted": False,
                "succeeded": True,
                "paths": [],
                "errors": [],
            },
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        change_set.status = "failed"
        change_set.apply_report_json = report
        await db.flush()
        raise WorkspaceExecutionError(
            409,
            "Workspace target changed since preview",
            "baseline_changed",
            report,
        )

    change_set.status = "applying"
    change_set.apply_report_json = {
        "status": "applying",
        "phase": "apply",
        "started_at": started_at.isoformat(),
    }
    await db.commit()

    attempted: list[tuple[FilePatch, str | None]] = []
    file_reports: list[dict] = []
    try:
        for patch in patches:
            if not patch.has_changes:
                patch.status = "unchanged"
                file_reports.append(
                    {
                        "path": patch.target_path,
                        "status": "unchanged",
                        "created": False,
                        "backup_path": None,
                        "bytes_written": 0,
                    }
                )
                continue

            _ensure_baseline_unchanged(mount, patch)
            attempted.append((patch, originals[patch.target_path]))
            write_report = write_mount_file(
                mount,
                patch.target_path,
                patch.proposed_content,
            )
            patch.status = "applied"
            file_reports.append(
                {
                    "path": patch.target_path,
                    "status": "applied",
                    "created": write_report["created"],
                    "backup_path": write_report["backup_path"],
                    "bytes_written": write_report["bytes_written"],
                }
            )
    except Exception as exc:
        error = _normalize_apply_error(exc)
        rollback = _rollback_attempted_files(mount, attempted)
        rolled_back_paths = set(rollback["paths"])
        for patch in patches:
            if patch.target_path in rolled_back_paths:
                patch.status = "rolled_back" if rollback["succeeded"] else "rollback_failed"
            elif patch.status not in {"unchanged"}:
                patch.status = "not_applied"
        report = {
            "status": "failed",
            "phase": "apply",
            "error_code": error.error_code,
            "error_message": error.detail,
            "file_count": len(patches),
            "changed_count": sum(patch.has_changes for patch in patches),
            "files": file_reports,
            "rollback": rollback,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        change_set.status = "failed"
        change_set.apply_report_json = report
        await db.flush()
        raise WorkspaceExecutionError(
            error.status_code,
            error.detail,
            error.error_code,
            report,
        ) from exc

    completed_at = datetime.now(UTC)
    report = {
        "status": "applied",
        "phase": "apply",
        "file_count": len(patches),
        "changed_count": sum(patch.has_changes for patch in patches),
        "total_bytes_written": sum(item["bytes_written"] for item in file_reports),
        "files": file_reports,
        "rollback": {
            "attempted": False,
            "succeeded": True,
            "paths": [],
            "errors": [],
        },
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
    }
    change_set.status = "applied"
    change_set.applied_at = completed_at
    change_set.apply_report_json = report
    await db.flush()
    return change_set


def workspace_change_set_to_dict(change_set: WorkspaceChangeSet) -> dict:
    patches = sorted(change_set.patches, key=lambda patch: patch.target_path)
    return {
        "id": change_set.id,
        "project_id": change_set.project_id,
        "task_graph_id": change_set.task_graph_id,
        "task_node_id": change_set.task_node_id,
        "mount_id": change_set.mount_id,
        "source_artifact_id": change_set.source_artifact_id,
        "status": change_set.status,
        "has_changes": any(patch.has_changes for patch in patches),
        "apply_report": change_set.apply_report_json,
        "applied_at": _as_utc(change_set.applied_at),
        "created_at": _as_utc(change_set.created_at),
        "updated_at": _as_utc(change_set.updated_at),
        "patches": [
            {
                "id": patch.id,
                "target_path": patch.target_path,
                "operation": patch.operation,
                "status": patch.status,
                "has_changes": patch.has_changes,
                "unified_diff": patch.unified_diff,
                "base_fingerprint": {
                    "exists": patch.base_exists,
                    "size": patch.base_size,
                    "sha256": patch.base_sha256,
                },
                "created_at": _as_utc(patch.created_at),
                "updated_at": _as_utc(patch.updated_at),
            }
            for patch in patches
        ],
    }


async def _load_task_node_for_user(
    db: AsyncSession,
    graph_id: str,
    node_key: str,
    user_id: str,
) -> tuple[TaskGraph, TaskNode]:
    result = await db.execute(
        select(TaskNode)
        .join(TaskGraph, TaskNode.task_graph_id == TaskGraph.id)
        .join(Project, TaskGraph.project_id == Project.id)
        .where(
            TaskGraph.id == graph_id,
            TaskNode.node_key == node_key,
            Project.user_id == user_id,
        )
        .options(selectinload(TaskNode.task_graph))
    )
    node = result.scalar_one_or_none()
    if node is None:
        raise WorkspaceExecutionError(404, "TaskNode not found", "task_node_not_found")
    return node.task_graph, node


async def _load_workspace_mount(
    db: AsyncSession,
    project_id: str,
    mount_id: str,
    user_id: str,
) -> ProjectMount:
    result = await db.execute(
        select(ProjectMount)
        .join(Project, ProjectMount.project_id == Project.id)
        .where(
            ProjectMount.id == mount_id,
            ProjectMount.project_id == project_id,
            Project.user_id == user_id,
        )
    )
    mount = result.scalar_one_or_none()
    if mount is None:
        raise WorkspaceExecutionError(404, "ProjectMount not found", "mount_not_found")
    if mount.mount_type != "local" or mount.status != "connected" or mount.role != "primary":
        raise WorkspaceExecutionError(
            409,
            "Workspace writes require a connected local primary mount",
            "mount_not_writable",
        )
    return mount


async def _validate_source_artifact(
    db: AsyncSession,
    *,
    project_id: str,
    artifact_id: str,
    user_id: str,
) -> None:
    artifact_id_result = await db.scalar(
        select(Artifact.id)
        .join(Project, Artifact.project_id == Project.id)
        .where(
            Artifact.id == artifact_id,
            Artifact.project_id == project_id,
            Project.user_id == user_id,
        )
    )
    if artifact_id_result is None:
        raise WorkspaceExecutionError(404, "Artifact not found", "artifact_not_found")


def _normalize_proposals(
    node: TaskNode,
    mount: ProjectMount,
    proposals: list[FileProposal],
) -> list[FileProposal]:
    if not proposals:
        raise WorkspaceExecutionError(400, "At least one file is required", "files_required")
    if len(proposals) > MAX_PATCH_FILES:
        raise WorkspaceExecutionError(413, "Too many files in change set", "too_many_files")
    if not node.target_files:
        raise WorkspaceExecutionError(
            400,
            "TaskNode does not declare target files",
            "target_files_required",
        )

    try:
        allowed_paths = {
            normalize_mount_relative_path(mount, target_path)
            for target_path in node.target_files
        }
    except BridgeAccessError as exc:
        raise _workspace_error_from_bridge(exc) from exc

    normalized: list[FileProposal] = []
    seen: set[str] = set()
    total_bytes = 0
    for proposal in proposals:
        try:
            target_path = normalize_mount_relative_path(mount, proposal.path)
        except BridgeAccessError as exc:
            raise _workspace_error_from_bridge(exc) from exc
        if target_path in seen:
            raise WorkspaceExecutionError(400, "Duplicate patch path", "duplicate_path")
        if target_path not in allowed_paths:
            raise WorkspaceExecutionError(
                400,
                f"Patch path is not declared by TaskNode: {target_path}",
                "path_not_declared",
            )
        seen.add(target_path)
        content_bytes = len(proposal.content.encode("utf-8"))
        if content_bytes > MAX_PATCH_FILE_BYTES:
            raise WorkspaceExecutionError(413, "Patch file is too large", "file_too_large")
        total_bytes += content_bytes
        if total_bytes > MAX_PATCH_TOTAL_BYTES:
            raise WorkspaceExecutionError(
                413,
                "Change set content is too large",
                "change_set_too_large",
            )
        normalized.append(FileProposal(path=target_path, content=proposal.content))
    return normalized


def _read_baseline(mount: ProjectMount, target_path: str) -> tuple[str, dict]:
    try:
        result = read_mount_file(mount, target_path, max_bytes=MAX_PATCH_FILE_BYTES)
    except BridgeAccessError as exc:
        if exc.status_code == 404:
            return "", {"exists": False, "size": 0, "sha256": None}
        raise _workspace_error_from_bridge(exc) from exc
    if result["truncated"]:
        raise WorkspaceExecutionError(413, "Target file is too large", "target_too_large")
    content = str(result["content"])
    return content, {
        "exists": True,
        "size": int(result["size"]),
        "sha256": _sha256(content),
    }


def _unified_diff(
    old_content: str,
    new_content: str,
    target_path: str,
    *,
    base_exists: bool,
) -> str:
    diff = "".join(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{target_path}" if base_exists else "/dev/null",
            tofile=f"b/{target_path}",
        )
    )
    if not diff and not base_exists:
        return f"--- /dev/null\n+++ b/{target_path}\n"
    return diff


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _mount_root_sha256(mount: ProjectMount) -> str:
    try:
        root = root_path_for_mount(mount)
    except BridgeAccessError as exc:
        raise _workspace_error_from_bridge(exc) from exc
    return _sha256(str(root))


def _validate_apply_scope(change_set: WorkspaceChangeSet) -> None:
    mount = change_set.mount
    node = change_set.task_node
    if (
        mount.project_id != change_set.project_id
        or mount.mount_type != "local"
        or mount.status != "connected"
        or mount.role != "primary"
    ):
        raise WorkspaceExecutionError(
            409,
            "Workspace mount is no longer writable",
            "mount_not_writable",
        )
    if _mount_root_sha256(mount) != change_set.mount_root_sha256:
        raise WorkspaceExecutionError(
            409,
            "Workspace mount authorization changed since preview",
            "mount_authorization_changed",
        )
    if node.task_graph_id != change_set.task_graph_id:
        raise WorkspaceExecutionError(
            409,
            "TaskNode scope changed since preview",
            "task_scope_changed",
        )

    try:
        allowed_paths = {
            normalize_mount_relative_path(mount, path)
            for path in (node.target_files or [])
        }
        patch_paths = {
            normalize_mount_relative_path(mount, patch.target_path)
            for patch in change_set.patches
        }
    except BridgeAccessError as exc:
        raise _workspace_error_from_bridge(exc) from exc
    if not patch_paths.issubset(allowed_paths):
        raise WorkspaceExecutionError(
            409,
            "TaskNode target files changed since preview",
            "task_scope_changed",
        )


def _patch_fingerprint(patch: FilePatch) -> dict:
    return {
        "exists": patch.base_exists,
        "size": patch.base_size,
        "sha256": patch.base_sha256,
    }


def _baseline_matches(patch: FilePatch, fingerprint: dict) -> bool:
    return (
        patch.base_exists == fingerprint["exists"]
        and patch.base_sha256 == fingerprint["sha256"]
    )


def _ensure_baseline_unchanged(mount: ProjectMount, patch: FilePatch) -> None:
    _content, fingerprint = _read_baseline(mount, patch.target_path)
    if not _baseline_matches(patch, fingerprint):
        raise WorkspaceExecutionError(
            409,
            f"Workspace target changed during apply: {patch.target_path}",
            "baseline_changed",
            {
                "path": patch.target_path,
                "expected": _patch_fingerprint(patch),
                "actual": fingerprint,
            },
        )


def _rollback_attempted_files(
    mount: ProjectMount,
    attempted: list[tuple[FilePatch, str | None]],
) -> dict:
    paths: list[str] = []
    errors: list[dict] = []
    for patch, original_content in reversed(attempted):
        paths.append(patch.target_path)
        try:
            restore_mount_file(mount, patch.target_path, original_content)
        except Exception as exc:
            errors.append({"path": patch.target_path, "error": str(exc)[:500]})
    return {
        "attempted": bool(attempted),
        "succeeded": not errors,
        "paths": paths,
        "errors": errors,
    }


def _normalize_apply_error(exc: Exception) -> WorkspaceExecutionError:
    if isinstance(exc, WorkspaceExecutionError):
        return exc
    if isinstance(exc, BridgeAccessError):
        return _workspace_error_from_bridge(exc)
    return WorkspaceExecutionError(
        500,
        "Workspace apply failed unexpectedly",
        "write_failed",
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _workspace_error_from_bridge(exc: BridgeAccessError) -> WorkspaceExecutionError:
    return WorkspaceExecutionError(
        exc.status_code,
        exc.detail,
        "bridge_access_error",
    )
