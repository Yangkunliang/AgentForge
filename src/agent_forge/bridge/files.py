"""Safe file access for user-authorized project mounts."""

from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from agent_forge.config import settings
from agent_forge.models import ProjectMount

MAX_FILE_BYTES = 200_000

IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "__pycache__",
}

SENSITIVE_FILE_NAMES = {
    ".npmrc",
    ".pypirc",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
}

SENSITIVE_SUFFIXES = (
    ".key",
    ".pem",
    ".p12",
    ".pfx",
)


class BridgeAccessError(Exception):
    """HTTP-friendly Bridge file access error."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def create_upload_mount_manifest(
    *,
    project_id: str,
    upload_id: str,
    files: list[dict[str, Any]],
    relative_paths: list[str],
) -> dict[str, Any]:
    """Persist user-uploaded UTF-8 files and return a manifest for ProjectMount metadata."""
    if not files:
        raise BridgeAccessError(400, "At least one file is required")
    if len(files) > settings.upload_mount_max_files:
        raise BridgeAccessError(400, f"Upload mount supports at most {settings.upload_mount_max_files} files")
    if relative_paths and len(relative_paths) != len(files):
        raise BridgeAccessError(400, "Upload paths must match uploaded files")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", upload_id):
        raise BridgeAccessError(400, "Invalid upload collection id")

    upload_root = Path(settings.upload_mount_dir).expanduser().resolve(strict=False)
    collection_dir = upload_root / upload_id
    allowed_extensions = _allowed_upload_extensions()
    manifest: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    total_bytes = 0
    uploaded_at = datetime.now(timezone.utc).isoformat()

    try:
        collection_dir.mkdir(parents=True, exist_ok=False)
        for index, file_info in enumerate(files):
            filename = str(file_info.get("filename") or "")
            content = bytes(file_info.get("content") or b"")
            content_type = str(file_info.get("content_type") or "text/plain")
            relative_path = _normalize_upload_path(relative_paths[index] if relative_paths else filename)
            if relative_path in seen_paths:
                raise BridgeAccessError(400, "Duplicate upload path is not allowed")
            seen_paths.add(relative_path)

            extension = PurePosixPath(relative_path).suffix.lower()
            if extension not in allowed_extensions:
                raise BridgeAccessError(400, f"Upload file extension is not allowed: {extension or '<none>'}")
            if len(content) > settings.upload_mount_max_file_bytes:
                raise BridgeAccessError(
                    400,
                    f"Upload file exceeds {settings.upload_mount_max_file_bytes} bytes",
                )
            total_bytes += len(content)
            if total_bytes > settings.upload_mount_max_total_bytes:
                raise BridgeAccessError(
                    400,
                    f"Upload mount exceeds {settings.upload_mount_max_total_bytes} total bytes",
                )
            try:
                content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise BridgeAccessError(415, "Only UTF-8 text files can be uploaded") from exc

            storage_path = relative_path
            target_path = _resolve_upload_storage_path(collection_dir, storage_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(content)
            manifest.append(
                {
                    "path": relative_path,
                    "name": PurePosixPath(relative_path).name,
                    "size": len(content),
                    "mime_type": content_type,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "storage_path": storage_path,
                    "uploaded_at": uploaded_at,
                }
            )
    except Exception:
        if collection_dir.exists():
            shutil.rmtree(collection_dir, ignore_errors=True)
        raise

    return {
        "created_from": "upload_mount_api",
        "project_id": project_id,
        "upload_id": upload_id,
        "file_count": len(manifest),
        "total_bytes": total_bytes,
        "uploaded_at": uploaded_at,
        "manifest": manifest,
    }


def root_path_for_mount(mount: ProjectMount) -> Path:
    """Return the canonical root path recorded by a local ProjectMount."""
    metadata = mount.metadata_json or {}
    raw_root = metadata.get("root_path") or mount.locator
    root = Path(str(raw_root)).expanduser().resolve(strict=False)
    if not root.exists() or not root.is_dir():
        raise BridgeAccessError(409, "Mount root is unavailable")
    return root


def list_mount_files(mount: ProjectMount, relative_path: str = "") -> dict[str, Any]:
    """List non-sensitive files/directories under an authorized mount root."""
    if mount.mount_type == "upload":
        return list_upload_mount_files(mount, relative_path)
    if mount.mount_type != "local":
        raise BridgeAccessError(400, "Only local or upload mounts support file access")
    root = root_path_for_mount(mount)
    target = _resolve_under_root(root, relative_path, allow_root=True)
    if not target.exists():
        raise BridgeAccessError(404, "Path not found")
    if not target.is_dir():
        raise BridgeAccessError(400, "Path must be a directory")

    entries: list[dict[str, Any]] = []
    for child in sorted(target.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower())):
        if child.is_dir() and child.name in IGNORED_DIR_NAMES:
            continue
        if _is_sensitive_path(child):
            continue
        stat_result = child.stat()
        entries.append(
            {
                "name": child.name,
                "relative_path": child.relative_to(root).as_posix(),
                "kind": "directory" if child.is_dir() else "file",
                "size": None if child.is_dir() else stat_result.st_size,
                "modified_at": datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc),
            }
        )

    normalized_path = "" if target == root else target.relative_to(root).as_posix()
    return {
        "mount_id": mount.id,
        "project_id": mount.project_id,
        "path": normalized_path,
        "entries": entries,
    }


def read_mount_file(
    mount: ProjectMount,
    relative_path: str,
    *,
    max_bytes: int = MAX_FILE_BYTES,
) -> dict[str, Any]:
    """Read UTF-8 text content from a file under an authorized mount root."""
    if mount.mount_type == "upload":
        return read_upload_mount_file(mount, relative_path, max_bytes=max_bytes)
    if mount.mount_type != "local":
        raise BridgeAccessError(400, "Only local or upload mounts support file access")
    root = root_path_for_mount(mount)
    target = _resolve_under_root(root, relative_path, allow_root=False)
    if not target.exists():
        raise BridgeAccessError(404, "Path not found")
    if not target.is_file():
        raise BridgeAccessError(400, "Path must be a file")

    raw = target.read_bytes()
    stat_result = target.stat()
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BridgeAccessError(415, "Only UTF-8 text files can be read") from exc

    return {
        "mount_id": mount.id,
        "project_id": mount.project_id,
        "path": target.relative_to(root).as_posix(),
        "content": content,
        "size": stat_result.st_size,
        "mtime_ns": stat_result.st_mtime_ns,
        "modified_at": datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc),
        "truncated": truncated,
    }


def normalize_mount_relative_path(mount: ProjectMount, relative_path: str) -> str:
    """Validate and normalize a file path under an authorized mount root."""
    root = root_path_for_mount(mount)
    target = _resolve_under_root(root, relative_path, allow_root=False, operation_label="accessed")
    return target.relative_to(root).as_posix()


def write_mount_file(mount: ProjectMount, relative_path: str, content: str) -> dict[str, Any]:
    """Write UTF-8 text content to a file under an authorized mount root."""
    if mount.mount_type != "local":
        raise BridgeAccessError(400, "Only local mounts support file writeback")
    root = root_path_for_mount(mount)
    target = _resolve_under_root(root, relative_path, allow_root=False, operation_label="written")
    if target.exists() and not target.is_file():
        raise BridgeAccessError(400, "Path must be a file")
    if target.parent.exists() and not target.parent.is_dir():
        raise BridgeAccessError(400, "Parent path must be a directory")

    created = not target.exists()
    backup_relative_path: str | None = None
    if target.exists():
        backup = _backup_path_for(target)
        backup.write_bytes(target.read_bytes())
        backup_relative_path = backup.relative_to(root).as_posix()

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return {
        "path": target.relative_to(root).as_posix(),
        "backup_path": backup_relative_path,
        "bytes_written": len(content.encode("utf-8")),
        "created": created,
        "updated_at": datetime.now(timezone.utc),
    }


def restore_mount_file(
    mount: ProjectMount,
    relative_path: str,
    original_content: str | None,
) -> dict[str, Any]:
    """Restore an attempted workspace write without creating another backup."""
    if mount.mount_type != "local":
        raise BridgeAccessError(400, "Only local mounts support file restore")
    root = root_path_for_mount(mount)
    target = _resolve_under_root(
        root,
        relative_path,
        allow_root=False,
        operation_label="restored",
    )
    if target.exists() and not target.is_file():
        raise BridgeAccessError(400, "Path must be a file")

    if original_content is None:
        if target.exists():
            target.unlink()
        return {"path": target.relative_to(root).as_posix(), "restored": True, "removed": True}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(original_content, encoding="utf-8")
    return {"path": target.relative_to(root).as_posix(), "restored": True, "removed": False}


def list_upload_mount_files(mount: ProjectMount, relative_path: str = "") -> dict[str, Any]:
    """List virtual files/directories from an upload mount manifest."""
    current_path = _normalize_upload_path(relative_path, allow_root=True)
    manifest = _upload_manifest(mount)
    prefix = f"{current_path}/" if current_path else ""
    entries_by_path: dict[str, dict[str, Any]] = {}
    exact_file = False

    for item in manifest:
        item_path = _normalize_upload_path(str(item.get("path") or ""))
        if item_path == current_path:
            exact_file = True
            continue
        if prefix and not item_path.startswith(prefix):
            continue
        rest = item_path[len(prefix):] if prefix else item_path
        if not rest:
            continue
        name, _, remainder = rest.partition("/")
        child_path = f"{prefix}{name}" if prefix else name
        if remainder:
            entries_by_path.setdefault(
                child_path,
                {
                    "name": name,
                    "relative_path": child_path,
                    "kind": "directory",
                    "size": None,
                    "modified_at": _parse_upload_datetime(item.get("uploaded_at")),
                },
            )
        else:
            entries_by_path[child_path] = {
                "name": name,
                "relative_path": child_path,
                "kind": "file",
                "size": int(item.get("size") or 0),
                "modified_at": _parse_upload_datetime(item.get("uploaded_at")),
            }

    if not entries_by_path:
        if exact_file:
            raise BridgeAccessError(400, "Path must be a directory")
        raise BridgeAccessError(404, "Path not found")

    entries = sorted(entries_by_path.values(), key=lambda item: (item["kind"] != "directory", item["name"].lower()))
    return {
        "mount_id": mount.id,
        "project_id": mount.project_id,
        "path": current_path,
        "entries": entries,
    }


def read_upload_mount_file(
    mount: ProjectMount,
    relative_path: str,
    *,
    max_bytes: int = MAX_FILE_BYTES,
) -> dict[str, Any]:
    """Read UTF-8 text content from an uploaded manifest file."""
    normalized_path = _normalize_upload_path(relative_path)
    manifest = _upload_manifest(mount)
    item = next(
        (
            entry
            for entry in manifest
            if _normalize_upload_path(str(entry.get("path") or "")) == normalized_path
        ),
        None,
    )
    if item is None:
        raise BridgeAccessError(404, "Path not found")

    upload_id = _upload_id_for_mount(mount)
    collection_dir = Path(settings.upload_mount_dir).expanduser().resolve(strict=False) / upload_id
    if not collection_dir.exists():
        raise BridgeAccessError(409, "Upload mount storage is unavailable")
    storage_path = _normalize_upload_path(str(item.get("storage_path") or item.get("path") or ""))
    target = _resolve_upload_storage_path(collection_dir, storage_path)
    if not target.exists() or not target.is_file():
        raise BridgeAccessError(404, "Path not found")

    raw = target.read_bytes()
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BridgeAccessError(415, "Only UTF-8 text files can be read") from exc

    return {
        "mount_id": mount.id,
        "project_id": mount.project_id,
        "path": normalized_path,
        "content": content,
        "size": int(item.get("size") or target.stat().st_size),
        "mtime_ns": target.stat().st_mtime_ns,
        "modified_at": _parse_upload_datetime(item.get("uploaded_at")),
        "truncated": truncated,
    }


def delete_upload_mount_files(mount: ProjectMount) -> None:
    """Remove persisted files for an upload mount if a collection exists."""
    try:
        upload_id = _upload_id_for_mount(mount)
    except BridgeAccessError:
        return
    collection_dir = Path(settings.upload_mount_dir).expanduser().resolve(strict=False) / upload_id
    if collection_dir.exists():
        shutil.rmtree(collection_dir, ignore_errors=True)


def _resolve_under_root(
    root: Path,
    relative_path: str,
    *,
    allow_root: bool,
    operation_label: str = "read",
) -> Path:
    value = (relative_path or "").strip()
    if value in ("", ".") and allow_root:
        return root
    if value in ("", "."):
        raise BridgeAccessError(400, "Path is required")

    requested = Path(value)
    if requested.is_absolute():
        raise BridgeAccessError(400, "Path must be relative to the mount root")
    if any(part == ".." for part in requested.parts):
        raise BridgeAccessError(400, "Path traversal is not allowed")

    target = (root / requested).resolve(strict=False)
    if target != root and not target.is_relative_to(root):
        raise BridgeAccessError(400, "Path traversal is not allowed")
    if _is_sensitive_path(target):
        raise BridgeAccessError(403, f"Sensitive files cannot be {operation_label} through Agent Bridge")
    return target


def _normalize_upload_path(path: str, *, allow_root: bool = False) -> str:
    value = (path or "").strip()
    if value in ("", ".") and allow_root:
        return ""
    if value in ("", "."):
        raise BridgeAccessError(400, "Path is required")
    if any(ord(char) < 32 for char in value):
        raise BridgeAccessError(400, "Path contains control characters")
    if "\\" in value:
        raise BridgeAccessError(400, "Path must use forward slashes")
    if re.match(r"^[A-Za-z]:", value):
        raise BridgeAccessError(400, "Path must be relative")

    upload_path = PurePosixPath(value)
    if upload_path.is_absolute():
        raise BridgeAccessError(400, "Path must be relative")
    if any(part == ".." for part in upload_path.parts):
        raise BridgeAccessError(400, "Path traversal is not allowed")
    return upload_path.as_posix()


def _resolve_upload_storage_path(collection_dir: Path, storage_path: str) -> Path:
    normalized = _normalize_upload_path(storage_path)
    target = (collection_dir / normalized).resolve(strict=False)
    if target != collection_dir and not target.is_relative_to(collection_dir):
        raise BridgeAccessError(400, "Path traversal is not allowed")
    return target


def _allowed_upload_extensions() -> set[str]:
    return {
        item.strip().lower()
        for item in settings.upload_mount_allowed_extensions.split(",")
        if item.strip()
    }


def _upload_manifest(mount: ProjectMount) -> list[dict[str, Any]]:
    metadata = mount.metadata_json or {}
    manifest = metadata.get("manifest")
    if not isinstance(manifest, list) or not manifest:
        raise BridgeAccessError(409, "Upload mount manifest is unavailable")
    return [item for item in manifest if isinstance(item, dict)]


def _upload_id_for_mount(mount: ProjectMount) -> str:
    metadata = mount.metadata_json or {}
    raw_upload_id = str(metadata.get("upload_id") or "").strip()
    if not raw_upload_id and mount.locator.startswith("upload://"):
        raw_upload_id = mount.locator.removeprefix("upload://").strip()
    if not raw_upload_id or not re.fullmatch(r"[A-Za-z0-9_-]+", raw_upload_id):
        raise BridgeAccessError(409, "Upload mount collection is unavailable")
    return raw_upload_id


def _parse_upload_datetime(value: object) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _backup_path_for(target: Path) -> Path:
    backup = target.with_name(f"{target.name}.agentforge.bak")
    if not backup.exists():
        return backup

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return target.with_name(f"{target.name}.agentforge.{timestamp}.bak")


def _is_sensitive_path(path: Path) -> bool:
    for part in path.parts:
        name = part.lower()
        if name == ".env" or name.startswith(".env."):
            return True
        if name in SENSITIVE_FILE_NAMES:
            return True
        if name.endswith(SENSITIVE_SUFFIXES):
            return True
    return False
