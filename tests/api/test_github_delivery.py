"""GitHub PR delivery API tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import Artifact, AuditLog, OAuthCredential, User
from agent_forge.security.credentials import encrypt_secret


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


@dataclass
class FakeGitHubFile:
    content: str
    sha: str = "file-sha-1"


class FakeGitHubDeliveryClient:
    def __init__(self) -> None:
        self.base_sha = "base-sha-1"
        self.file = FakeGitHubFile("print('old')\n")
        self.created_branches: list[dict[str, Any]] = []
        self.commits: list[dict[str, Any]] = []
        self.pull_requests: list[dict[str, Any]] = []

    async def get_branch_sha(self, repo_full_name: str, branch: str) -> str:
        assert repo_full_name == "acme/shop-api"
        assert branch == "main"
        return self.base_sha

    async def get_file(self, repo_full_name: str, path: str, ref: str) -> dict[str, Any] | None:
        assert repo_full_name == "acme/shop-api"
        assert path == "src/main.py"
        assert ref == self.base_sha
        return {"content": self.file.content, "sha": self.file.sha}

    async def create_branch(self, repo_full_name: str, branch: str, base_sha: str) -> None:
        self.created_branches.append({"repo": repo_full_name, "branch": branch, "base_sha": base_sha})

    async def put_file(
        self,
        repo_full_name: str,
        path: str,
        content: str,
        branch: str,
        message: str,
        file_sha: str | None,
    ) -> dict[str, Any]:
        self.commits.append(
            {
                "repo": repo_full_name,
                "path": path,
                "content": content,
                "branch": branch,
                "message": message,
                "file_sha": file_sha,
            }
        )
        return {"commit_sha": "commit-sha-1", "html_url": "https://github.com/acme/shop-api/commit/commit-sha-1"}

    async def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        self.pull_requests.append(
            {
                "repo": repo_full_name,
                "title": title,
                "body": body,
                "head": head,
                "base": base,
            }
        )
        return {"number": 42, "html_url": "https://github.com/acme/shop-api/pull/42"}


async def test_github_delivery_preview_returns_diff_without_exposing_token(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from api.routes import projects as project_routes

    fake_client = FakeGitHubDeliveryClient()
    project, mount, artifact = await _create_github_delivery_fixture(async_client, fake_user, db_session)

    def create_fake_client(access_token: str):
        assert access_token == "gho_task024_secret"
        return fake_client

    monkeypatch.setattr(project_routes, "create_github_delivery_client", create_fake_client)

    resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/github/preview",
        json={
            "mount_id": mount["id"],
            "target_path": "src/main.py",
            "base_branch": "main",
            "target_branch": "agentforge/task-024",
            "pr_title": "Update main.py",
        },
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 200
    preview = resp.json()
    assert preview["status"] == "previewed"
    assert preview["project_id"] == project["id"]
    assert preview["mount_id"] == mount["id"]
    assert preview["target_path"] == "src/main.py"
    assert preview["has_changes"] is True
    assert "-print('old')" in preview["unified_diff"]
    assert "+print('new')" in preview["unified_diff"]
    assert preview["report"]["delivery_channel"] == "github_pr"
    assert preview["report"]["repo_full_name"] == "acme/shop-api"
    assert preview["report"]["base_branch"] == "main"
    assert preview["report"]["target_branch"] == "agentforge/task-024"
    assert preview["report"]["base_sha"] == "base-sha-1"
    assert preview["report"]["target_file_sha"] == "file-sha-1"
    assert fake_client.created_branches == []
    assert fake_client.commits == []
    assert fake_client.pull_requests == []
    assert "gho_task024_secret" not in str(preview)

    audits = await _delivery_audits(db_session, artifact["id"])
    assert "delivery.github.preview.succeeded" in [audit.action for audit in audits]
    assert "gho_task024_secret" not in str([audit.details for audit in audits])


async def test_github_delivery_apply_requires_confirmation(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from api.routes import projects as project_routes

    fake_client = FakeGitHubDeliveryClient()
    _project, mount, artifact = await _create_github_delivery_fixture(async_client, fake_user, db_session)
    monkeypatch.setattr(project_routes, "create_github_delivery_client", lambda _token: fake_client)

    resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/github/apply",
        json={
            "mount_id": mount["id"],
            "target_path": "src/main.py",
            "base_branch": "main",
            "target_branch": "agentforge/task-024",
            "confirm_write": False,
            "expected_base_sha": "base-sha-1",
        },
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 409
    assert fake_client.created_branches == []
    assert fake_client.commits == []
    assert fake_client.pull_requests == []

    audits = await _delivery_audits(db_session, artifact["id"])
    denied = next(audit for audit in audits if audit.action == "delivery.github.apply.denied")
    assert denied.details["reason"] == "missing_confirmation"
    assert "gho_task024_secret" not in str(denied.details)


async def test_github_delivery_apply_rejects_changed_base_ref_and_persists_failed_report(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from api.routes import projects as project_routes

    fake_client = FakeGitHubDeliveryClient()
    _project, mount, artifact = await _create_github_delivery_fixture(async_client, fake_user, db_session)
    monkeypatch.setattr(project_routes, "create_github_delivery_client", lambda _token: fake_client)

    preview_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/github/preview",
        json={"mount_id": mount["id"], "target_path": "src/main.py", "base_branch": "main"},
        headers=_auth_headers(fake_user),
    )
    assert preview_resp.status_code == 200
    expected_base_sha = preview_resp.json()["report"]["base_sha"]
    fake_client.base_sha = "base-sha-2"

    apply_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/github/apply",
        json={
            "mount_id": mount["id"],
            "target_path": "src/main.py",
            "base_branch": "main",
            "target_branch": "agentforge/task-024",
            "confirm_write": True,
            "expected_base_sha": expected_base_sha,
        },
        headers=_auth_headers(fake_user),
    )

    assert apply_resp.status_code == 409
    assert apply_resp.json()["detail"] == "GitHub base branch changed since preview"
    assert fake_client.created_branches == []
    assert fake_client.commits == []
    assert fake_client.pull_requests == []

    delivered_artifact = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}",
        headers=_auth_headers(fake_user),
    ).json()
    assert delivered_artifact["delivery_status"] == "failed"
    assert delivered_artifact["delivery_report"]["error_code"] == "github_base_changed"
    assert delivered_artifact["delivery_report"]["phase"] == "consistency_check"
    assert delivered_artifact["delivery_report"]["expected_base_sha"] == expected_base_sha
    assert delivered_artifact["delivery_report"]["actual_base_sha"] == "base-sha-2"
    assert "gho_task024_secret" not in str(delivered_artifact)

    audits = await _delivery_audits(db_session, artifact["id"])
    assert "delivery.github.apply.conflict" in [audit.action for audit in audits]
    assert "gho_task024_secret" not in str([audit.details for audit in audits])


async def test_github_delivery_apply_creates_branch_commit_pr_and_report(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from api.routes import projects as project_routes

    fake_client = FakeGitHubDeliveryClient()
    _project, mount, artifact = await _create_github_delivery_fixture(async_client, fake_user, db_session)
    monkeypatch.setattr(project_routes, "create_github_delivery_client", lambda _token: fake_client)

    resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/github/apply",
        json={
            "mount_id": mount["id"],
            "target_path": "src/main.py",
            "base_branch": "main",
            "target_branch": "agentforge/task-024",
            "pr_title": "Update main.py",
            "commit_message": "Update generated artifact",
            "confirm_write": True,
            "expected_base_sha": "base-sha-1",
        },
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 200
    delivered = resp.json()
    assert delivered["status"] == "delivered"
    assert delivered["report"]["delivery_channel"] == "github_pr"
    assert delivered["report"]["pr_url"] == "https://github.com/acme/shop-api/pull/42"
    assert delivered["report"]["commit_sha"] == "commit-sha-1"
    assert delivered["report"]["recovery_hint"]
    assert fake_client.created_branches == [
        {"repo": "acme/shop-api", "branch": "agentforge/task-024", "base_sha": "base-sha-1"}
    ]
    assert fake_client.commits[0]["content"] == "print('new')\n"
    assert fake_client.commits[0]["file_sha"] == "file-sha-1"
    assert fake_client.pull_requests[0]["head"] == "agentforge/task-024"
    assert fake_client.pull_requests[0]["base"] == "main"
    assert "gho_task024_secret" not in str(delivered)

    delivered_artifact = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}",
        headers=_auth_headers(fake_user),
    ).json()
    assert delivered_artifact["delivery_status"] == "delivered"
    assert delivered_artifact["delivery_target_path"] == "github://acme/shop-api/src/main.py"
    assert delivered_artifact["delivery_report"]["pr_url"] == "https://github.com/acme/shop-api/pull/42"
    assert delivered_artifact["delivery_report"]["commit_sha"] == "commit-sha-1"

    report_resp = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}/delivery/report",
        headers=_auth_headers(fake_user),
    )
    assert report_resp.status_code == 200
    assert "https://github.com/acme/shop-api/pull/42" in report_resp.text
    assert "commit-sha-1" in report_resp.text

    audits = await _delivery_audits(db_session, artifact["id"])
    actions = [audit.action for audit in audits]
    assert "delivery.github.apply.branch_created" in actions
    assert "delivery.github.apply.commit_created" in actions
    assert "delivery.github.apply.pr_created" in actions
    assert "delivery.github.apply.succeeded" in actions
    assert "gho_task024_secret" not in str([audit.details for audit in audits])


async def _create_github_delivery_fixture(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    project = async_client.post(
        "/api/v1/projects",
        json={"name": f"GitHub PR 交付项目 {uuid.uuid4().hex[:8]}"},
        headers=_auth_headers(fake_user),
    ).json()

    credential_id = f"github-cred-{uuid.uuid4().hex}"
    db_session.add(
        OAuthCredential(
            id=credential_id,
            user_id=fake_user.id,
            provider="github",
            name="acme/shop-api",
            encrypted_access_token=encrypt_secret("gho_task024_secret"),
            scopes_json=["repo"],
            metadata_json={"repo_full_name": "acme/shop-api"},
        )
    )
    await db_session.commit()

    mount = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts",
        json={
            "mount_type": "github",
            "display_name": "GitHub acme/shop-api",
            "locator": "github://acme/shop-api",
            "role": "primary",
            "status": "connected",
            "metadata": {
                "repo_full_name": "acme/shop-api",
                "default_branch": "main",
                "credential_id": credential_id,
            },
        },
        headers=_auth_headers(fake_user),
    ).json()

    artifact = async_client.post(
        f"/api/v1/projects/{project['id']}/artifacts",
        json={
            "artifact_type": "code",
            "name": "main.py",
            "content": "print('new')\n",
            "file_type": "text",
        },
        headers=_auth_headers(fake_user),
    ).json()
    return project, mount, artifact


async def _delivery_audits(db_session: AsyncSession, artifact_id: str) -> list[AuditLog]:
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.resource == "artifact_delivery")
        .where(AuditLog.details["artifact_id"].as_string() == artifact_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(result.scalars().all())
