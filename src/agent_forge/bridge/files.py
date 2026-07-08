"""Safe file access for user-authorized local project mounts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    root = root_path_for_mount(mount)
    target = _resolve_under_root(root, relative_path, allow_root=False)
    if not target.exists():
        raise BridgeAccessError(404, "Path not found")
    if not target.is_file():
        raise BridgeAccessError(400, "Path must be a file")

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
        "path": target.relative_to(root).as_posix(),
        "content": content,
        "size": target.stat().st_size,
        "truncated": truncated,
    }


def normalize_mount_relative_path(mount: ProjectMount, relative_path: str) -> str:
    """Validate and normalize a file path under an authorized mount root."""
    root = root_path_for_mount(mount)
    target = _resolve_under_root(root, relative_path, allow_root=False, operation_label="accessed")
    return target.relative_to(root).as_posix()


def write_mount_file(mount: ProjectMount, relative_path: str, content: str) -> dict[str, Any]:
    """Write UTF-8 text content to a file under an authorized mount root."""
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
