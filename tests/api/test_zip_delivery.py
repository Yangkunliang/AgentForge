"""Zip delivery API tests."""

from __future__ import annotations

import json
import os
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token, hash_password
from agent_forge.models import AuditLog, User
from middleware.auth import get_current_user


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


async def test_zip_delivery_preview_reports_package_without_writing_file(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    monkeypatch,
):
    package_dir = _configure_package_dir(monkeypatch, tmp_path)
    project, artifact = _create_artifact(async_client, fake_user)

    resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/preview",
        json={"target_path": "docs/architecture.md"},
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 200
    preview = resp.json()
    assert preview["status"] == "previewed"
    assert preview["project_id"] == project["id"]
    assert preview["mount_id"] == "zip"
    assert preview["target_path"] == "docs/architecture.md"
    assert preview["has_changes"] is True
    assert preview["unified_diff"] == ""
    assert preview["report"]["delivery_channel"] == "zip"
    assert preview["report"]["file_count"] == 1
    assert preview["report"]["total_bytes"] == len(artifact["content"].encode("utf-8"))
    assert len(preview["report"]["package_sha256"]) == 64
    assert preview["report"]["files"][0]["path"] == "docs/architecture.md"
    assert str(package_dir) not in str(preview)
    assert list(package_dir.glob("*.zip")) == []


async def test_zip_delivery_apply_creates_downloadable_package_and_report(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    db_session: AsyncSession,
    monkeypatch,
):
    package_dir = _configure_package_dir(monkeypatch, tmp_path)
    _project, artifact = _create_artifact(async_client, fake_user)

    denied_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/apply",
        json={"target_path": "docs/architecture.md", "confirm_write": False},
        headers=_auth_headers(fake_user),
    )
    assert denied_resp.status_code == 409
    assert list(package_dir.glob("*.zip")) == []

    apply_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/apply",
        json={"target_path": "docs/architecture.md", "confirm_write": True},
        headers=_auth_headers(fake_user),
    )

    assert apply_resp.status_code == 200
    delivered = apply_resp.json()
    assert delivered["status"] == "delivered"
    assert delivered["report"]["delivery_channel"] == "zip"
    assert delivered["report"]["download_url"] == f"/api/v1/artifacts/{artifact['id']}/delivery/zip/download"
    assert delivered["report"]["package_name"].endswith(".zip")
    assert len(delivered["report"]["package_sha256"]) == 64
    assert "package_path" not in str(delivered)
    assert str(package_dir) not in str(delivered)

    package_files = list(package_dir.glob("*.zip"))
    assert len(package_files) == 1

    artifact_resp = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}",
        headers=_auth_headers(fake_user),
    )
    assert artifact_resp.status_code == 200
    delivered_artifact = artifact_resp.json()
    assert delivered_artifact["delivery_status"] == "delivered"
    assert delivered_artifact["delivery_target_path"].startswith("zip://")
    assert delivered_artifact["delivery_report"]["package_sha256"] == delivered["report"]["package_sha256"]

    download_resp = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/download",
        headers=_auth_headers(fake_user),
    )
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"].startswith("application/zip")

    archive = zipfile.ZipFile(BytesIO(download_resp.content))
    assert sorted(archive.namelist()) == [
        "delivery-report.md",
        "files/docs/architecture.md",
        "manifest.json",
    ]
    assert archive.read("files/docs/architecture.md").decode("utf-8") == artifact["content"]
    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["artifact_id"] == artifact["id"]
    assert manifest["project_id"] == artifact["project_id"]
    assert manifest["file_count"] == 1
    assert manifest["files"][0]["path"] == "docs/architecture.md"
    assert manifest["files"][0]["sha256"]

    audits = await _delivery_audits(db_session, artifact["id"])
    actions = [audit.action for audit in audits]
    assert "delivery.zip.apply.denied" in actions
    assert "delivery.zip.apply.succeeded" in actions
    assert str(package_dir) not in str([audit.details for audit in audits])


def test_zip_delivery_rejects_unsafe_or_duplicate_package_paths(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    monkeypatch,
):
    _configure_package_dir(monkeypatch, tmp_path)
    _project, artifact = _create_artifact(async_client, fake_user)

    traversal_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/preview",
        json={"target_path": "../secret.md"},
        headers=_auth_headers(fake_user),
    )
    assert traversal_resp.status_code == 400

    backslash_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/preview",
        json={"target_path": "docs\\secret.md"},
        headers=_auth_headers(fake_user),
    )
    assert backslash_resp.status_code == 400

    drive_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/preview",
        json={"target_path": "C:/secret.md"},
        headers=_auth_headers(fake_user),
    )
    assert drive_resp.status_code == 400

    duplicate_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/preview",
        json={
            "files": [
                {"path": "docs/architecture.md", "content": "one"},
                {"path": "docs/architecture.md", "content": "two"},
            ],
        },
        headers=_auth_headers(fake_user),
    )
    assert duplicate_resp.status_code == 400


async def test_zip_delivery_download_is_scoped_to_artifact_owner(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    db_session: AsyncSession,
    monkeypatch,
):
    from api.main import app

    _configure_package_dir(monkeypatch, tmp_path)
    _project, artifact = _create_artifact(async_client, fake_user)
    apply_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/apply",
        json={"target_path": "docs/architecture.md", "confirm_write": True},
        headers=_auth_headers(fake_user),
    )
    assert apply_resp.status_code == 200

    other_user = User(
        id="zip-other-user",
        username="zip-other-user",
        email="zip-other@example.com",
        password_hash=hash_password("TestPass123"),
        permissions=["read"],
    )
    db_session.add(other_user)
    await db_session.commit()

    async def override_other_user():
        return other_user

    previous_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override_other_user
    try:
        download_resp = async_client.get(
            f"/api/v1/artifacts/{artifact['id']}/delivery/zip/download",
            headers=_auth_headers(other_user),
        )
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_current_user] = previous_override

    assert download_resp.status_code == 404


def test_zip_delivery_apply_cleans_expired_packages(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    monkeypatch,
):
    package_dir = _configure_package_dir(monkeypatch, tmp_path)
    old_package = package_dir / "old-package.zip"
    old_package.write_bytes(b"old")
    old_time = time.time() - (49 * 60 * 60)
    os.utime(old_package, (old_time, old_time))
    _project, artifact = _create_artifact(async_client, fake_user)

    apply_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/zip/apply",
        json={"target_path": "docs/architecture.md", "confirm_write": True},
        headers=_auth_headers(fake_user),
    )

    assert apply_resp.status_code == 200
    assert not old_package.exists()
    assert len(list(package_dir.glob("*.zip"))) == 1


def _configure_package_dir(monkeypatch, tmp_path: Path) -> Path:
    from api.routes import projects as project_routes

    package_dir = tmp_path / "delivery-packages"
    package_dir.mkdir()
    monkeypatch.setattr(project_routes.settings, "delivery_package_dir", str(package_dir))
    monkeypatch.setattr(project_routes.settings, "delivery_package_ttl_hours", 24)
    return package_dir


def _create_artifact(
    async_client: TestClient,
    fake_user: User,
) -> tuple[dict[str, Any], dict[str, Any]]:
    project = async_client.post(
        "/api/v1/projects",
        json={"name": "zip 交付项目"},
        headers=_auth_headers(fake_user),
    ).json()
    artifact = async_client.post(
        f"/api/v1/projects/{project['id']}/artifacts",
        json={
            "artifact_type": "code",
            "name": "architecture.md",
            "content": "# 架构设计\n\n- FastAPI\n- Vue 3\n",
            "file_type": "markdown",
        },
        headers=_auth_headers(fake_user),
    ).json()
    return project, artifact


async def _delivery_audits(db_session: AsyncSession, artifact_id: str) -> list[AuditLog]:
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.resource == "artifact_delivery")
        .where(AuditLog.details["artifact_id"].as_string() == artifact_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(result.scalars().all())
