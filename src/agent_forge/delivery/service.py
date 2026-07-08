"""Preview and apply Artifact delivery back to authorized project mounts."""

from __future__ import annotations

import difflib
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


def preview_artifact_delivery(artifact: Artifact, mount: ProjectMount, target_path: str) -> dict[str, Any]:
    """Build a unified diff without modifying the target mount."""
    normalized_target = _normalize_target_path(mount, target_path)
    old_content = _read_existing_content(mount, normalized_target)
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
        },
    }


async def apply_artifact_delivery(
    db: AsyncSession,
    artifact: Artifact,
    mount: ProjectMount,
    target_path: str,
) -> dict[str, Any]:
    """Write Artifact content to an authorized mount and persist delivery status."""
    preview = preview_artifact_delivery(artifact, mount, target_path)
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


def build_delivery_report_markdown(artifact: Artifact) -> str:
    """Render a delivered Artifact report as Markdown."""
    report = artifact.delivery_report_json or {}
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


def _read_existing_content(mount: ProjectMount, target_path: str) -> str:
    try:
        result = read_mount_file(mount, target_path)
    except BridgeAccessError as exc:
        if exc.status_code == 404:
            return ""
        raise
    if result["truncated"]:
        raise BridgeAccessError(413, "Target file is too large to preview safely")
    return str(result["content"])


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
