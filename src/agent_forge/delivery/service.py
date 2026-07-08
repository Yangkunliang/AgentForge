"""Preview and apply Artifact delivery back to authorized project mounts."""

from __future__ import annotations

import difflib
import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.bridge.files import (
    BridgeAccessError,
    normalize_mount_relative_path,
    read_mount_file,
    write_mount_file,
)
from agent_forge.models import Artifact, ProjectMount


class DeliveryConsistencyError(Exception):
    """Raised when a confirmed write no longer matches the previewed target."""

    def __init__(self, detail: str, report: dict[str, Any]) -> None:
        super().__init__(detail)
        self.detail = detail
        self.report = report


def preview_artifact_delivery(artifact: Artifact, mount: ProjectMount, target_path: str) -> dict[str, Any]:
    """Build a unified diff without modifying the target mount."""
    normalized_target = _normalize_target_path(mount, target_path)
    old_content, target_fingerprint = _read_existing_content(mount, normalized_target)
    new_content = artifact.content
    unified_diff = _unified_diff(old_content, new_content, normalized_target)

    return {
        "artifact_id": artifact.id,
        "project_id": artifact.project_id,
        "mount_id": mount.id,
        "target_path": normalized_target,
        "status": "previewed",
        "has_changes": old_content != new_content,
        "unified_diff": unified_diff,
        "report": {
            "mount_id": mount.id,
            "target_path": normalized_target,
            "existing_file": old_content != "",
            "bytes_to_write": len(new_content.encode("utf-8")),
            "target_fingerprint": target_fingerprint,
        },
    }


async def apply_artifact_delivery(
    db: AsyncSession,
    artifact: Artifact,
    mount: ProjectMount,
    target_path: str,
    *,
    expected_target_hash: str | None = None,
) -> dict[str, Any]:
    """Write Artifact content to an authorized mount and persist delivery status."""
    preview = preview_artifact_delivery(artifact, mount, target_path)
    actual_hash = preview["report"]["target_fingerprint"]["sha256"]
    if expected_target_hash is not None and actual_hash != expected_target_hash:
        report = await mark_artifact_delivery_failed(
            db,
            artifact,
            mount,
            preview["target_path"],
            phase="consistency_check",
            error_code="target_changed",
            error_message="Target file changed since preview",
            recovery_hint="Preview the diff again before confirming delivery.",
            target_fingerprint=preview["report"]["target_fingerprint"],
            extra={"expected_target_hash": expected_target_hash},
        )
        raise DeliveryConsistencyError("Target file changed since preview", report)

    write_report = write_mount_file(mount, preview["target_path"], artifact.content)
    delivery_report = {
        **preview["report"],
        "backup_path": write_report["backup_path"],
        "bytes_written": write_report["bytes_written"],
        "created": write_report["created"],
        "updated_at": write_report["updated_at"].isoformat(),
    }

    artifact.delivery_status = "delivered"
    artifact.delivery_target_path = preview["target_path"]
    artifact.delivered_at = datetime.now(UTC)
    artifact.delivery_report_json = delivery_report
    await db.flush()

    return {
        **preview,
        "status": "delivered",
        "report": delivery_report,
    }


async def mark_artifact_delivery_failed(
    db: AsyncSession,
    artifact: Artifact,
    mount: ProjectMount,
    target_path: str,
    *,
    phase: str,
    error_code: str,
    error_message: str,
    recovery_hint: str,
    target_fingerprint: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a readable failed delivery report on the Artifact."""
    report = {
        "status": "failed",
        "phase": phase,
        "mount_id": mount.id,
        "target_path": target_path,
        "error_code": error_code,
        "error_message": error_message,
        "recovery_hint": recovery_hint,
    }
    if target_fingerprint is not None:
        report["target_fingerprint"] = target_fingerprint
    if extra:
        report.update(extra)

    artifact.delivery_status = "failed"
    artifact.delivery_target_path = target_path
    artifact.delivery_report_json = report
    await db.flush()
    return report


def build_delivery_report_markdown(artifact: Artifact) -> str:
    """Render a delivered Artifact report as Markdown."""
    report = artifact.delivery_report_json or {}
    if report.get("delivery_channel") == "github_pr":
        delivered_at = artifact.delivered_at.isoformat() if artifact.delivered_at else report.get("delivered_at", "未记录")
        return "\n".join(
            [
                f"# Delivery Report: {artifact.name}",
                "",
                f"- Artifact ID: {artifact.id}",
                f"- Project ID: {artifact.project_id}",
                f"- Status: {artifact.delivery_status}",
                f"- Channel: GitHub Pull Request",
                f"- Repository: {report.get('repo_full_name') or '未记录'}",
                f"- Target Path: {artifact.delivery_target_path or report.get('delivery_target_path') or '未记录'}",
                f"- Base Branch: {report.get('base_branch') or '未记录'}",
                f"- Delivery Branch: {report.get('target_branch') or '未记录'}",
                f"- PR URL: {report.get('pr_url') or '未记录'}",
                f"- Commit SHA: {report.get('commit_sha') or '未记录'}",
                f"- Delivered At: {delivered_at}",
                "",
                "## Recovery",
                "",
                report.get("recovery_hint") or "未记录",
                "",
            ]
        )
    if report.get("delivery_channel") == "zip":
        delivered_at = artifact.delivered_at.isoformat() if artifact.delivered_at else report.get("delivered_at", "未记录")
        files = report.get("files") if isinstance(report.get("files"), list) else []
        lines = [
            f"# Delivery Report: {artifact.name}",
            "",
            f"- Artifact ID: {artifact.id}",
            f"- Project ID: {artifact.project_id}",
            f"- Status: {artifact.delivery_status}",
            f"- Channel: Zip Package",
            f"- Package: {report.get('package_name') or '未记录'}",
            f"- Package SHA256: {report.get('package_sha256') or '未记录'}",
            f"- File Count: {report.get('file_count') or 0}",
            f"- Total Bytes: {report.get('total_bytes') or 0}",
            f"- Expires At: {report.get('expires_at') or '未记录'}",
            f"- Delivered At: {delivered_at}",
            "",
            "## Files",
            "",
        ]
        for item in files:
            if isinstance(item, dict):
                lines.append(f"- `{item.get('path')}` ({item.get('size')} bytes, sha256 `{item.get('sha256')}`)")
        lines.extend(["", "## Recovery", "", report.get("recovery_hint") or "未记录", ""])
        return "\n".join(lines)

    target_path = artifact.delivery_target_path or report.get("target_path") or "未记录"
    backup_path = report.get("backup_path") or "无"
    bytes_written = report.get("bytes_written") or 0
    delivered_at = artifact.delivered_at.isoformat() if artifact.delivered_at else "未记录"

    return "\n".join(
        [
            f"# Delivery Report: {artifact.name}",
            "",
            f"- Artifact ID: {artifact.id}",
            f"- Project ID: {artifact.project_id}",
            f"- Status: {artifact.delivery_status}",
            f"- Target Path: {target_path}",
            f"- Backup Path: {backup_path}",
            f"- Bytes Written: {bytes_written}",
            f"- Delivered At: {delivered_at}",
            "",
        ]
    )


def _normalize_target_path(mount: ProjectMount, target_path: str) -> str:
    return normalize_mount_relative_path(mount, target_path)


def _read_existing_content(mount: ProjectMount, target_path: str) -> tuple[str, dict[str, Any]]:
    try:
        result = read_mount_file(mount, target_path)
    except BridgeAccessError as exc:
        if exc.status_code == 404:
            return "", _missing_fingerprint()
        raise
    if result["truncated"]:
        raise BridgeAccessError(413, "Target file is too large to preview safely")
    content = str(result["content"])
    return content, {
        "exists": True,
        "size": result["size"],
        "mtime_ns": result.get("mtime_ns"),
        "sha256": _sha256_text(content),
    }


def _unified_diff(old_content: str, new_content: str, target_path: str) -> str:
    lines = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        fromfile=f"a/{target_path}",
        tofile=f"b/{target_path}",
        lineterm="",
    )
    diff = "\n".join(lines)
    return f"{diff}\n" if diff else ""


def _missing_fingerprint() -> dict[str, Any]:
    return {
        "exists": False,
        "size": 0,
        "mtime_ns": None,
        "sha256": None,
    }


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
