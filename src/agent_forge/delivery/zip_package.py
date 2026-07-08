"""Zip package delivery for Artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Artifact

ZIP_MOUNT_ID = "zip"
ZIP_ENTRY_DATE = (2026, 1, 1, 0, 0, 0)


class ZipDeliveryError(Exception):
    """HTTP-friendly zip delivery error."""

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 400,
        phase: str = "preview",
        error_code: str = "zip_delivery_error",
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.phase = phase
        self.error_code = error_code


def preview_zip_delivery(
    artifact: Artifact,
    *,
    target_path: str | None = None,
    files: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build zip package metadata and checksum without writing a file."""
    package_files = _resolve_package_files(artifact, target_path=target_path, files=files)
    package_name = _package_name(artifact.name)
    zip_bytes = _build_zip_bytes(artifact, package_files)
    package_sha256 = _sha256_bytes(zip_bytes)
    total_bytes = sum(item["size"] for item in package_files)
    first_path = package_files[0]["path"]

    return {
        "artifact_id": artifact.id,
        "project_id": artifact.project_id,
        "mount_id": ZIP_MOUNT_ID,
        "target_path": first_path,
        "status": "previewed",
        "has_changes": True,
        "unified_diff": "",
        "report": {
            "delivery_channel": "zip",
            "mount_id": ZIP_MOUNT_ID,
            "target_path": first_path,
            "package_name": package_name,
            "file_count": len(package_files),
            "total_bytes": total_bytes,
            "package_sha256": package_sha256,
            "files": _public_file_entries(package_files),
        },
    }


async def apply_zip_delivery(
    db: AsyncSession,
    artifact: Artifact,
    *,
    target_path: str | None,
    files: list[dict[str, str]] | None,
    package_dir: Path,
    ttl_hours: int,
) -> dict[str, Any]:
    """Persist a downloadable zip package and update Artifact delivery state."""
    now = datetime.now(UTC)
    _cleanup_expired_packages(package_dir, ttl_hours=ttl_hours, now=now)

    preview = preview_zip_delivery(artifact, target_path=target_path, files=files)
    package_files = _resolve_package_files(artifact, target_path=target_path, files=files)
    zip_bytes = _build_zip_bytes(artifact, package_files)
    package_sha256 = _sha256_bytes(zip_bytes)
    package_id = uuid.uuid4().hex
    package_name = preview["report"]["package_name"]
    package_dir.mkdir(parents=True, exist_ok=True)
    package_path = _package_path(package_dir, artifact.id, package_id)
    package_path.write_bytes(zip_bytes)
    expires_at = now + timedelta(hours=ttl_hours)

    delivery_report = {
        **preview["report"],
        "status": "delivered",
        "package_id": package_id,
        "package_sha256": package_sha256,
        "download_url": f"/api/v1/artifacts/{artifact.id}/delivery/zip/download",
        "expires_at": expires_at.isoformat(),
        "recovery_hint": "Download the zip package before it expires, then apply the files manually to your project.",
        "delivered_at": now.isoformat(),
    }

    artifact.delivery_status = "delivered"
    artifact.delivery_target_path = f"zip://{package_id}/{package_name}"
    artifact.delivered_at = now
    artifact.delivery_report_json = delivery_report
    await db.flush()

    return {
        **preview,
        "status": "delivered",
        "report": delivery_report,
    }


async def mark_zip_delivery_failed(
    db: AsyncSession,
    artifact: Artifact,
    *,
    target_path: str,
    phase: str,
    error_code: str,
    error_message: str,
    recovery_hint: str,
) -> dict[str, Any]:
    """Persist a readable failed zip delivery report on the Artifact."""
    report = {
        "delivery_channel": "zip",
        "status": "failed",
        "phase": phase,
        "mount_id": ZIP_MOUNT_ID,
        "target_path": target_path,
        "error_code": error_code,
        "error_message": error_message,
        "recovery_hint": recovery_hint,
    }
    artifact.delivery_status = "failed"
    artifact.delivery_target_path = f"zip://failed/{target_path}"
    artifact.delivery_report_json = report
    await db.flush()
    return report


def zip_download_path(artifact: Artifact, package_dir: Path) -> tuple[Path, str]:
    """Return the server path and filename for an authorized zip delivery."""
    report = artifact.delivery_report_json or {}
    if artifact.delivery_status != "delivered" or report.get("delivery_channel") != "zip":
        raise ZipDeliveryError("Artifact has not been delivered as a zip package", status_code=409, phase="download")
    package_id = str(report.get("package_id") or "").strip()
    package_name = str(report.get("package_name") or f"{artifact.name}.zip").strip()
    expires_at = _parse_expires_at(report.get("expires_at"))
    if expires_at and expires_at < datetime.now(UTC):
        raise ZipDeliveryError("Zip delivery package has expired", status_code=410, phase="download")
    package_path = _package_path(package_dir, artifact.id, package_id)
    if not package_path.exists():
        raise ZipDeliveryError("Zip delivery package is unavailable", status_code=404, phase="download")
    return package_path, package_name


def _resolve_package_files(
    artifact: Artifact,
    *,
    target_path: str | None,
    files: list[dict[str, str]] | None,
) -> list[dict[str, Any]]:
    if files:
        raw_files = files
    else:
        raw_files = [{"path": target_path or artifact.name, "content": artifact.content}]

    seen: set[str] = set()
    package_files: list[dict[str, Any]] = []
    for raw_file in raw_files:
        path = _normalize_package_path(str(raw_file.get("path") or ""))
        if path in seen:
            raise ZipDeliveryError("Duplicate package path is not allowed")
        seen.add(path)
        content = str(raw_file.get("content") if raw_file.get("content") is not None else artifact.content)
        encoded = content.encode("utf-8")
        package_files.append(
            {
                "path": path,
                "archive_path": f"files/{path}",
                "content": content,
                "size": len(encoded),
                "sha256": _sha256_bytes(encoded),
            }
        )

    if not package_files:
        raise ZipDeliveryError("At least one file is required")
    return package_files


def _normalize_package_path(path: str) -> str:
    value = path.strip()
    if value in ("", "."):
        raise ZipDeliveryError("Package path is required")
    if any(ord(char) < 32 for char in value):
        raise ZipDeliveryError("Package path contains control characters")
    if "\\" in value:
        raise ZipDeliveryError("Package path must use forward slashes")
    if re.match(r"^[A-Za-z]:", value):
        raise ZipDeliveryError("Package path must be relative")

    package_path = PurePosixPath(value)
    if package_path.is_absolute():
        raise ZipDeliveryError("Package path must be relative")
    if any(part == ".." for part in package_path.parts):
        raise ZipDeliveryError("Package path traversal is not allowed")
    return package_path.as_posix()


def _build_zip_bytes(artifact: Artifact, package_files: list[dict[str, Any]]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest = _build_manifest(artifact, package_files)
        _write_zip_entry(archive, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        _write_zip_entry(archive, "delivery-report.md", _build_zip_report(artifact, package_files))
        for package_file in package_files:
            _write_zip_entry(archive, package_file["archive_path"], package_file["content"])
    return buffer.getvalue()


def _build_manifest(artifact: Artifact, package_files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_id": artifact.id,
        "project_id": artifact.project_id,
        "artifact_name": artifact.name,
        "file_count": len(package_files),
        "total_bytes": sum(item["size"] for item in package_files),
        "files": _public_file_entries(package_files),
    }


def _build_zip_report(artifact: Artifact, package_files: list[dict[str, Any]]) -> str:
    lines = [
        f"# Zip Delivery Report: {artifact.name}",
        "",
        f"- Artifact ID: {artifact.id}",
        f"- Project ID: {artifact.project_id}",
        f"- File Count: {len(package_files)}",
        f"- Total Bytes: {sum(item['size'] for item in package_files)}",
        "",
        "## Files",
        "",
    ]
    for package_file in package_files:
        lines.append(f"- `{package_file['path']}` ({package_file['size']} bytes, sha256 `{package_file['sha256']}`)")
    lines.append("")
    return "\n".join(lines)


def _write_zip_entry(archive: zipfile.ZipFile, name: str, content: str) -> None:
    info = zipfile.ZipInfo(name, ZIP_ENTRY_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, content.encode("utf-8"))


def _public_file_entries(package_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "path": item["path"],
            "archive_path": item["archive_path"],
            "size": item["size"],
            "sha256": item["sha256"],
        }
        for item in package_files
    ]


def _cleanup_expired_packages(package_dir: Path, *, ttl_hours: int, now: datetime) -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    cutoff = now.timestamp() - (ttl_hours * 60 * 60)
    for package_path in package_dir.glob("*.zip"):
        try:
            if package_path.stat().st_mtime < cutoff:
                package_path.unlink()
        except FileNotFoundError:
            continue


def _package_path(package_dir: Path, artifact_id: str, package_id: str) -> Path:
    if not package_id:
        raise ZipDeliveryError("Zip delivery package id is missing", status_code=409, phase="download")
    if not re.fullmatch(r"[0-9a-f]{32}", package_id):
        raise ZipDeliveryError("Zip delivery package id is invalid", status_code=409, phase="download")
    return package_dir / f"{artifact_id}-{package_id}.zip"


def _package_name(artifact_name: str) -> str:
    normalized_name = (artifact_name.strip() or "artifact").replace("\\", "/")
    safe_name = PurePosixPath(normalized_name).name
    return f"{safe_name}.zip" if not safe_name.endswith(".zip") else safe_name


def _parse_expires_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
