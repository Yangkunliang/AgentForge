"""GitHub Pull Request delivery for Artifacts."""

from __future__ import annotations

import asyncio
import base64
import difflib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Artifact, ProjectMount

SENSITIVE_FILE_NAMES = {
    ".npmrc",
    ".pypirc",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
}
SENSITIVE_SUFFIXES = (".key", ".pem", ".p12", ".pfx")


class GitHubDeliveryError(Exception):
    """HTTP-friendly GitHub delivery error."""

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 502,
        phase: str = "apply",
        error_code: str = "github_api_error",
        report: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.phase = phase
        self.error_code = error_code
        self.report = report


class GitHubDeliveryConsistencyError(GitHubDeliveryError):
    """Raised when the remote base branch changed after preview."""


class GitHubDeliveryClient(Protocol):
    """Small GitHub API surface needed by PR delivery."""

    async def get_branch_sha(self, repo_full_name: str, branch: str) -> str:
        """Return the commit sha pointed to by a branch."""

    async def get_file(self, repo_full_name: str, path: str, ref: str) -> dict[str, Any] | None:
        """Return a UTF-8 text file at ref, or None when it does not exist."""

    async def create_branch(self, repo_full_name: str, branch: str, base_sha: str) -> None:
        """Create a branch from base sha."""

    async def put_file(
        self,
        repo_full_name: str,
        path: str,
        content: str,
        branch: str,
        message: str,
        file_sha: str | None,
    ) -> dict[str, Any]:
        """Create or update a file and return commit metadata."""

    async def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        """Open a pull request and return PR metadata."""


class GitHubRestDeliveryClient:
    """Minimal GitHub REST client used by production PR delivery."""

    def __init__(self, access_token: str) -> None:
        self.access_token = access_token

    async def get_branch_sha(self, repo_full_name: str, branch: str) -> str:
        data = await self._request_json(
            "GET",
            f"/repos/{_quote_repo(repo_full_name)}/git/ref/heads/{urllib.parse.quote(branch, safe='/')}",
        )
        obj = data.get("object") or {}
        sha = obj.get("sha")
        if not sha:
            raise GitHubDeliveryError("GitHub branch ref response is invalid", phase="preview")
        return str(sha)

    async def get_file(self, repo_full_name: str, path: str, ref: str) -> dict[str, Any] | None:
        query = urllib.parse.urlencode({"ref": ref})
        try:
            data = await self._request_json(
                "GET",
                f"/repos/{_quote_repo(repo_full_name)}/contents/{urllib.parse.quote(path)}?{query}",
            )
        except GitHubDeliveryError as exc:
            if exc.status_code == 404:
                return None
            raise

        raw_content = str(data.get("content") or "")
        encoding = str(data.get("encoding") or "")
        if encoding != "base64":
            raise GitHubDeliveryError("GitHub file response is not base64 encoded", phase="preview")
        try:
            content = base64.b64decode(raw_content).decode("utf-8")
        except Exception as exc:
            raise GitHubDeliveryError("Only UTF-8 text files can be delivered through GitHub PR") from exc
        return {"content": content, "sha": data.get("sha")}

    async def create_branch(self, repo_full_name: str, branch: str, base_sha: str) -> None:
        await self._request_json(
            "POST",
            f"/repos/{_quote_repo(repo_full_name)}/git/refs",
            payload={"ref": f"refs/heads/{branch}", "sha": base_sha},
            expected_statuses={201},
        )

    async def put_file(
        self,
        repo_full_name: str,
        path: str,
        content: str,
        branch: str,
        message: str,
        file_sha: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if file_sha:
            payload["sha"] = file_sha

        data = await self._request_json(
            "PUT",
            f"/repos/{_quote_repo(repo_full_name)}/contents/{urllib.parse.quote(path)}",
            payload=payload,
            expected_statuses={200, 201},
        )
        commit = data.get("commit") or {}
        commit_sha = commit.get("sha")
        if not commit_sha:
            raise GitHubDeliveryError("GitHub file update response is missing commit sha")
        return {"commit_sha": commit_sha, "html_url": commit.get("html_url")}

    async def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        data = await self._request_json(
            "POST",
            f"/repos/{_quote_repo(repo_full_name)}/pulls",
            payload={"title": title, "body": body, "head": head, "base": base},
            expected_statuses={201},
        )
        pr_url = data.get("html_url")
        if not pr_url:
            raise GitHubDeliveryError("GitHub pull request response is missing URL")
        return {"number": data.get("number"), "html_url": pr_url}

    async def delete_branch(self, repo_full_name: str, branch: str) -> None:
        await self._request_json(
            "DELETE",
            f"/repos/{_quote_repo(repo_full_name)}/git/refs/heads/{urllib.parse.quote(branch, safe='/')}",
            expected_statuses={204},
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> dict[str, Any]:
        expected = expected_statuses or {200}
        return await asyncio.to_thread(self._request_json_sync, method, path, payload, expected)

    def _request_json_sync(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        expected_statuses: set[int],
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=body,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            detail = _github_error_message(raw) or exc.reason or "GitHub API request failed"
            raise GitHubDeliveryError(str(detail), status_code=exc.code) from exc
        except Exception as exc:
            raise GitHubDeliveryError(str(exc) or exc.__class__.__name__) from exc

        if status not in expected_statuses:
            raise GitHubDeliveryError(f"GitHub API returned unexpected status {status}", status_code=status)
        if not raw:
            return {}
        return json.loads(raw)


def create_github_delivery_client(access_token: str) -> GitHubDeliveryClient:
    """Build the production GitHub delivery client."""
    return GitHubRestDeliveryClient(access_token)


async def preview_github_pr_delivery(
    artifact: Artifact,
    mount: ProjectMount,
    client: GitHubDeliveryClient,
    *,
    target_path: str,
    base_branch: str | None = None,
    target_branch: str | None = None,
    pr_title: str | None = None,
) -> dict[str, Any]:
    """Build a GitHub file diff without creating remote state."""
    context = _github_mount_context(mount)
    normalized_target = _normalize_repo_path(target_path)
    base = _normalize_branch_name(base_branch or context["default_branch"])
    head = _normalize_branch_name(target_branch or _default_target_branch(artifact))
    title = (pr_title or f"Deliver {artifact.name}").strip()

    base_sha = await client.get_branch_sha(context["repo_full_name"], base)
    existing_file = await client.get_file(context["repo_full_name"], normalized_target, base_sha)
    old_content = str((existing_file or {}).get("content") or "")
    new_content = artifact.content
    file_sha = (existing_file or {}).get("sha")
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
            "delivery_channel": "github_pr",
            "mount_id": mount.id,
            "repo_full_name": context["repo_full_name"],
            "target_path": normalized_target,
            "delivery_target_path": _delivery_target_path(context["repo_full_name"], normalized_target),
            "base_branch": base,
            "target_branch": head,
            "base_sha": base_sha,
            "target_file_sha": file_sha,
            "pr_title": title,
            "existing_file": existing_file is not None,
            "bytes_to_write": len(new_content.encode("utf-8")),
        },
    }


async def apply_github_pr_delivery(
    db: AsyncSession,
    artifact: Artifact,
    mount: ProjectMount,
    client: GitHubDeliveryClient,
    *,
    target_path: str,
    base_branch: str | None,
    target_branch: str | None,
    pr_title: str | None,
    commit_message: str | None,
    expected_base_sha: str,
) -> dict[str, Any]:
    """Create a branch, commit Artifact content, and open a Pull Request."""
    preview = await preview_github_pr_delivery(
        artifact,
        mount,
        client,
        target_path=target_path,
        base_branch=base_branch,
        target_branch=target_branch,
        pr_title=pr_title,
    )
    report = dict(preview["report"])
    if report["base_sha"] != expected_base_sha:
        failed_report = await _mark_github_delivery_failed(
            db,
            artifact,
            report,
            phase="consistency_check",
            error_code="github_base_changed",
            error_message="GitHub base branch changed since preview",
            recovery_hint="Preview the GitHub diff again before confirming PR delivery.",
            extra={"expected_base_sha": expected_base_sha, "actual_base_sha": report["base_sha"]},
        )
        raise GitHubDeliveryConsistencyError(
            "GitHub base branch changed since preview",
            status_code=409,
            phase="consistency_check",
            error_code="github_base_changed",
            report=failed_report,
        )
    if not preview["has_changes"]:
        failed_report = await _mark_github_delivery_failed(
            db,
            artifact,
            report,
            phase="consistency_check",
            error_code="github_no_changes",
            error_message="Artifact content is identical to the target file",
            recovery_hint="No PR is needed. Update the Artifact or select a different target path.",
        )
        raise GitHubDeliveryError(
            "Artifact content is identical to the target file",
            status_code=409,
            phase="consistency_check",
            error_code="github_no_changes",
            report=failed_report,
        )

    repo_full_name = report["repo_full_name"]
    branch_created = False
    audit_events: list[dict[str, Any]] = []
    try:
        await client.create_branch(repo_full_name, report["target_branch"], expected_base_sha)
        branch_created = True
        audit_events.append(
            {
                "action": "delivery.github.apply.branch_created",
                "details": {
                    "repo_full_name": repo_full_name,
                    "target_branch": report["target_branch"],
                    "base_sha": expected_base_sha,
                },
            }
        )

        commit_result = await client.put_file(
            repo_full_name,
            report["target_path"],
            artifact.content,
            report["target_branch"],
            (commit_message or f"Deliver {artifact.name}").strip(),
            report.get("target_file_sha"),
        )
        commit_sha = str(commit_result["commit_sha"])
        commit_url = commit_result.get("html_url")
        audit_events.append(
            {
                "action": "delivery.github.apply.commit_created",
                "details": {
                    "repo_full_name": repo_full_name,
                    "target_branch": report["target_branch"],
                    "target_path": report["target_path"],
                    "commit_sha": commit_sha,
                },
            }
        )

        pr_result = await client.create_pull_request(
            repo_full_name,
            report["pr_title"],
            _build_pr_body(artifact, report, commit_sha),
            report["target_branch"],
            report["base_branch"],
        )
        pr_url = str(pr_result["html_url"])
        pr_number = pr_result.get("number")
        audit_events.append(
            {
                "action": "delivery.github.apply.pr_created",
                "details": {
                    "repo_full_name": repo_full_name,
                    "target_branch": report["target_branch"],
                    "base_branch": report["base_branch"],
                    "pr_url": pr_url,
                    "pr_number": pr_number,
                },
            }
        )
    except Exception as exc:
        cleanup_report = await _cleanup_unreferenced_branch(client, repo_full_name, report["target_branch"], branch_created)
        failed_report = await _mark_github_delivery_failed(
            db,
            artifact,
            report,
            phase="apply",
            error_code="github_api_error",
            error_message=str(exc) or exc.__class__.__name__,
            recovery_hint="Retry after checking the branch name, repository permissions, and GitHub status.",
            extra=cleanup_report,
        )
        raise GitHubDeliveryError(
            "GitHub PR delivery failed",
            phase="apply",
            error_code="github_api_error",
            report=failed_report,
        ) from exc

    delivery_report = {
        **report,
        "status": "delivered",
        "commit_sha": commit_sha,
        "commit_url": commit_url,
        "pr_url": pr_url,
        "pr_number": pr_number,
        "recovery_hint": "Review the PR before merge. To roll back before merge, close the PR and delete the delivery branch.",
        "delivered_at": datetime.now(UTC).isoformat(),
    }
    artifact.delivery_status = "delivered"
    artifact.delivery_target_path = report["delivery_target_path"]
    artifact.delivered_at = datetime.now(UTC)
    artifact.delivery_report_json = delivery_report
    await db.flush()

    return {
        **preview,
        "status": "delivered",
        "target_path": report["target_path"],
        "report": delivery_report,
        "_audit_events": audit_events,
    }


async def _mark_github_delivery_failed(
    db: AsyncSession,
    artifact: Artifact,
    report: dict[str, Any],
    *,
    phase: str,
    error_code: str,
    error_message: str,
    recovery_hint: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failed_report = {
        **report,
        "status": "failed",
        "phase": phase,
        "error_code": error_code,
        "error_message": error_message,
        "recovery_hint": recovery_hint,
    }
    if extra:
        failed_report.update(extra)
    artifact.delivery_status = "failed"
    artifact.delivery_target_path = report["delivery_target_path"]
    artifact.delivery_report_json = failed_report
    await db.flush()
    return failed_report


async def _cleanup_unreferenced_branch(
    client: GitHubDeliveryClient,
    repo_full_name: str,
    branch: str,
    branch_created: bool,
) -> dict[str, Any]:
    if not branch_created or not hasattr(client, "delete_branch"):
        return {"cleanup_attempted": False}
    try:
        await getattr(client, "delete_branch")(repo_full_name, branch)
    except Exception as exc:
        return {"cleanup_attempted": True, "cleanup_status": "failed", "cleanup_error": str(exc)}
    return {"cleanup_attempted": True, "cleanup_status": "deleted"}


def _github_mount_context(mount: ProjectMount) -> dict[str, str]:
    if mount.mount_type != "github":
        raise GitHubDeliveryError("Only GitHub mounts support PR delivery", status_code=400, phase="preview")
    if mount.status != "connected":
        raise GitHubDeliveryError("GitHub mount is not connected", status_code=409, phase="preview")
    metadata = mount.metadata_json or {}
    repo_full_name = str(metadata.get("repo_full_name") or "").strip()
    if "/" not in repo_full_name:
        raise GitHubDeliveryError("GitHub mount is missing repository metadata", status_code=409, phase="preview")
    return {
        "repo_full_name": repo_full_name,
        "default_branch": str(metadata.get("default_branch") or "main").strip() or "main",
    }


def _normalize_repo_path(target_path: str) -> str:
    value = (target_path or "").strip()
    if value in ("", "."):
        raise GitHubDeliveryError("Target path is required", status_code=400, phase="preview")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise GitHubDeliveryError("Target path must be relative to the repository root", status_code=400, phase="preview")
    if any(part == ".." for part in path.parts):
        raise GitHubDeliveryError("Path traversal is not allowed", status_code=400, phase="preview")
    if _is_sensitive_path(path):
        raise GitHubDeliveryError("Sensitive files cannot be delivered through GitHub PR", status_code=403, phase="preview")
    return path.as_posix()


def _normalize_branch_name(branch: str) -> str:
    value = (branch or "").strip()
    if not value:
        raise GitHubDeliveryError("Branch name is required", status_code=400, phase="preview")
    if value.startswith("refs/") or ".." in value or value.endswith("/") or "//" in value:
        raise GitHubDeliveryError("Branch name is not allowed", status_code=400, phase="preview")
    return value


def _default_target_branch(artifact: Artifact) -> str:
    return f"agentforge/{artifact.id[:8]}"


def _delivery_target_path(repo_full_name: str, target_path: str) -> str:
    return f"github://{repo_full_name}/{target_path}"


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


def _build_pr_body(artifact: Artifact, report: dict[str, Any], commit_sha: str) -> str:
    return "\n".join(
        [
            f"## AgentForge Delivery: {artifact.name}",
            "",
            f"- Artifact ID: {artifact.id}",
            f"- Project ID: {artifact.project_id}",
            f"- Target file: `{report['target_path']}`",
            f"- Base: `{report['base_branch']}` at `{report['base_sha']}`",
            f"- Delivery branch: `{report['target_branch']}`",
            f"- Commit SHA: `{commit_sha}`",
            "",
            "## Rollback",
            "",
            "Close this PR and delete the delivery branch before merge. After merge, revert the commit from GitHub.",
            "",
        ]
    )


def _is_sensitive_path(path: PurePosixPath) -> bool:
    for part in path.parts:
        name = part.lower()
        if name == ".env" or name.startswith(".env."):
            return True
        if name in SENSITIVE_FILE_NAMES:
            return True
        if name.endswith(SENSITIVE_SUFFIXES):
            return True
    return False


def _github_error_message(raw: str) -> str | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    message = data.get("message")
    if isinstance(message, str):
        return message
    return None


def _quote_repo(repo_full_name: str) -> str:
    owner, repo = repo_full_name.split("/", 1)
    return f"{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
