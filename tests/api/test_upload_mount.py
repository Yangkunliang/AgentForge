"""Upload mount API and Bridge tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token, hash_password
from agent_forge.models import AuditLog, User


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


async def test_upload_mount_uploads_manifest_and_reads_uploaded_text(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    db_session: AsyncSession,
    monkeypatch,
):
    upload_dir = _configure_upload_mount(monkeypatch, tmp_path)
    project = _create_project(async_client, fake_user)

    upload_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "需求文件包", "role": "docs", "paths": "docs/requirements.md"},
        files=[("files", ("requirements.md", b"# Requirements\n\n- login\n", "text/markdown"))],
        headers=_auth_headers(fake_user),
    )

    assert upload_resp.status_code == 201
    mount = upload_resp.json()
    assert mount["mount_type"] == "upload"
    assert mount["status"] == "connected"
    assert mount["locator"].startswith("upload://")
    assert mount["metadata"]["file_count"] == 1
    assert mount["metadata"]["total_bytes"] == len(b"# Requirements\n\n- login\n")
    assert mount["metadata"]["manifest"][0]["path"] == "docs/requirements.md"
    assert mount["metadata"]["manifest"][0]["mime_type"] == "text/markdown"
    assert "content" not in str(mount["metadata"])
    assert upload_dir.exists()

    status_resp = async_client.get(
        f"/api/v1/projects/{project['id']}/bridge/status",
        headers=_auth_headers(fake_user),
    )
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["connected_mounts"] == 1
    assert status_body["mounts"][0]["mount_type"] == "upload"
    assert status_body["mounts"][0]["root_path"] is None

    root_list_resp = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files",
        headers=_auth_headers(fake_user),
    )
    assert root_list_resp.status_code == 200
    assert root_list_resp.json()["entries"][0]["relative_path"] == "docs"
    assert root_list_resp.json()["entries"][0]["kind"] == "directory"

    docs_list_resp = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files",
        params={"path": "docs"},
        headers=_auth_headers(fake_user),
    )
    assert docs_list_resp.status_code == 200
    docs_entries = docs_list_resp.json()["entries"]
    assert docs_entries[0]["relative_path"] == "docs/requirements.md"
    assert docs_entries[0]["size"] == len(b"# Requirements\n\n- login\n")

    read_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files/read",
        json={"path": "docs/requirements.md"},
        headers=_auth_headers(fake_user),
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["content"] == "# Requirements\n\n- login\n"
    assert read_resp.json()["truncated"] is False

    audits = await _upload_mount_audits(db_session, project["id"])
    actions = [audit.action for audit in audits]
    assert "upload_mount.file.uploaded" in actions
    assert "upload_mount.file.read" in actions
    assert "Requirements" not in str([audit.details for audit in audits])


def test_upload_mount_rejects_unsafe_paths_and_disallowed_extensions(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    monkeypatch,
):
    _configure_upload_mount(monkeypatch, tmp_path)
    project = _create_project(async_client, fake_user)

    traversal_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "坏路径", "paths": "../secret.md"},
        files=[("files", ("secret.md", b"secret", "text/markdown"))],
        headers=_auth_headers(fake_user),
    )
    assert traversal_resp.status_code == 400

    backslash_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "坏路径", "paths": "docs\\secret.md"},
        files=[("files", ("secret.md", b"secret", "text/markdown"))],
        headers=_auth_headers(fake_user),
    )
    assert backslash_resp.status_code == 400

    extension_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "图片", "paths": "docs/screenshot.png"},
        files=[("files", ("screenshot.png", b"not image context", "image/png"))],
        headers=_auth_headers(fake_user),
    )
    assert extension_resp.status_code == 400


def test_upload_mount_rejects_file_count_size_and_non_utf8(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    monkeypatch,
):
    _configure_upload_mount(monkeypatch, tmp_path, max_files=1, max_file_bytes=8)
    project = _create_project(async_client, fake_user)

    count_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "太多文件"},
        files=[
            ("files", ("a.md", b"one", "text/markdown")),
            ("files", ("b.md", b"two", "text/markdown")),
        ],
        headers=_auth_headers(fake_user),
    )
    assert count_resp.status_code == 400

    size_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "过大文件", "paths": "docs/large.md"},
        files=[("files", ("large.md", b"123456789", "text/markdown"))],
        headers=_auth_headers(fake_user),
    )
    assert size_resp.status_code == 400

    binary_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "二进制", "paths": "docs/binary.md"},
        files=[("files", ("binary.md", b"\xff\xfe\x00\x00", "text/markdown"))],
        headers=_auth_headers(fake_user),
    )
    assert binary_resp.status_code == 415


async def test_upload_mount_read_is_scoped_and_manifest_bound(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    db_session: AsyncSession,
    monkeypatch,
):
    _configure_upload_mount(monkeypatch, tmp_path)
    project = _create_project(async_client, fake_user)
    upload_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "需求文件包", "paths": "docs/requirements.md"},
        files=[("files", ("requirements.md", b"# Requirements\n", "text/markdown"))],
        headers=_auth_headers(fake_user),
    )
    mount = upload_resp.json()

    missing_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files/read",
        json={"path": "docs/not-uploaded.md"},
        headers=_auth_headers(fake_user),
    )
    assert missing_resp.status_code == 404

    other_user = User(
        id="upload-other-user",
        username="upload-other-user",
        email="upload-other@example.com",
        password_hash=hash_password("TestPass123"),
        permissions=["read"],
    )
    db_session.add(other_user)
    await db_session.commit()

    from api.main import app
    from middleware.auth import get_current_user

    async def override_other_user():
        return other_user

    previous_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override_other_user
    try:
        other_resp = async_client.post(
            f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files/read",
            json={"path": "docs/requirements.md"},
            headers=_auth_headers(other_user),
        )
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_current_user] = previous_override
    assert other_resp.status_code == 404

    empty_manifest_mount = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts",
        json={
            "mount_type": "upload",
            "display_name": "空 manifest",
            "locator": "upload://missing",
            "role": "docs",
            "status": "connected",
            "metadata": {},
        },
        headers=_auth_headers(fake_user),
    ).json()
    empty_manifest_resp = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts/{empty_manifest_mount['id']}/files",
        headers=_auth_headers(fake_user),
    )
    assert empty_manifest_resp.status_code == 409


async def test_delete_upload_mount_writes_audit_and_removes_files(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    db_session: AsyncSession,
    monkeypatch,
):
    upload_dir = _configure_upload_mount(monkeypatch, tmp_path)
    project = _create_project(async_client, fake_user)
    upload_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/upload",
        data={"display_name": "需求文件包", "paths": "docs/requirements.md"},
        files=[("files", ("requirements.md", b"# Requirements\n", "text/markdown"))],
        headers=_auth_headers(fake_user),
    )
    mount = upload_resp.json()
    upload_id = mount["metadata"]["upload_id"]
    assert (upload_dir / upload_id).exists()

    delete_resp = async_client.delete(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}",
        headers=_auth_headers(fake_user),
    )
    assert delete_resp.status_code == 204
    assert not (upload_dir / upload_id).exists()

    audits = await _upload_mount_audits(db_session, project["id"])
    assert "upload_mount.deleted" in [audit.action for audit in audits]


def _configure_upload_mount(
    monkeypatch,
    tmp_path: Path,
    *,
    max_files: int = 5,
    max_file_bytes: int = 200_000,
) -> Path:
    from api.routes import projects as project_routes

    upload_dir = tmp_path / "upload-mounts"
    monkeypatch.setattr(project_routes.settings, "upload_mount_dir", str(upload_dir))
    monkeypatch.setattr(project_routes.settings, "upload_mount_max_files", max_files)
    monkeypatch.setattr(project_routes.settings, "upload_mount_max_file_bytes", max_file_bytes)
    monkeypatch.setattr(project_routes.settings, "upload_mount_max_total_bytes", 500_000)
    monkeypatch.setattr(project_routes.settings, "upload_mount_allowed_extensions", ".md,.txt,.py,.ts,.tsx,.vue,.json")
    return upload_dir


def _create_project(async_client: TestClient, fake_user: User) -> dict[str, Any]:
    return async_client.post(
        "/api/v1/projects",
        json={"name": "Upload Mount 项目"},
        headers=_auth_headers(fake_user),
    ).json()


async def _upload_mount_audits(db_session: AsyncSession, project_id: str) -> list[AuditLog]:
    result = await db_session.execute(
        select(AuditLog)
        .where(
            AuditLog.resource == "upload_mount",
            AuditLog.details["project_id"].as_string() == project_id,
        )
        .order_by(AuditLog.created_at.asc())
    )
    return list(result.scalars().all())
