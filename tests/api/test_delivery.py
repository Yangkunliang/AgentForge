"""Delivery API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import AuditLog, User


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


def test_delivery_preview_and_confirmed_apply_write_authorized_mount_file(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "shop-api"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    target = src_dir / "main.py"
    target.write_text("print('old')\n", encoding="utf-8")

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "交付项目"},
        headers=_auth_headers(fake_user),
    ).json()
    mount = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts",
        json={
            "mount_type": "local",
            "display_name": "shop-api",
            "locator": str(root),
            "role": "primary",
            "status": "connected",
            "metadata": {"root_path": str(root)},
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

    preview_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/preview",
        json={"mount_id": mount["id"], "target_path": "src/main.py"},
        headers=_auth_headers(fake_user),
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["status"] == "previewed"
    assert preview["target_path"] == "src/main.py"
    assert preview["has_changes"] is True
    assert "-print('old')" in preview["unified_diff"]
    assert "+print('new')" in preview["unified_diff"]
    assert preview["report"]["target_fingerprint"]["sha256"]
    assert preview["report"]["target_fingerprint"]["size"] == len("print('old')\n".encode("utf-8"))
    assert target.read_text(encoding="utf-8") == "print('old')\n"

    blocked_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/apply",
        json={"mount_id": mount["id"], "target_path": "src/main.py", "confirm_write": False},
        headers=_auth_headers(fake_user),
    )
    assert blocked_resp.status_code == 409
    assert target.read_text(encoding="utf-8") == "print('old')\n"

    apply_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/apply",
        json={"mount_id": mount["id"], "target_path": "src/main.py", "confirm_write": True},
        headers=_auth_headers(fake_user),
    )
    assert apply_resp.status_code == 200
    applied = apply_resp.json()
    assert applied["status"] == "delivered"
    assert applied["report"]["backup_path"] == "src/main.py.agentforge.bak"
    assert target.read_text(encoding="utf-8") == "print('new')\n"
    assert (src_dir / "main.py.agentforge.bak").read_text(encoding="utf-8") == "print('old')\n"

    delivered_artifact = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}",
        headers=_auth_headers(fake_user),
    ).json()
    assert delivered_artifact["delivery_status"] == "delivered"
    assert delivered_artifact["delivery_target_path"] == "src/main.py"
    assert delivered_artifact["delivery_report"]["mount_id"] == mount["id"]
    assert delivered_artifact["delivered_at"] is not None

    report_resp = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}/delivery/report",
        headers=_auth_headers(fake_user),
    )
    assert report_resp.status_code == 200
    assert report_resp.headers["content-type"].startswith("text/markdown")
    assert "src/main.py" in report_resp.text
    assert "src/main.py.agentforge.bak" in report_resp.text


async def test_delivery_apply_rejects_target_changed_after_preview(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    db_session: AsyncSession,
):
    root = tmp_path / "shop-api"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    target = src_dir / "main.py"
    target.write_text("print('old')\n", encoding="utf-8")

    project = _create_project(async_client, fake_user, "一致性交付项目")
    mount = _create_mount(async_client, fake_user, project["id"], root)
    artifact = _create_artifact(
        async_client,
        fake_user,
        project["id"],
        name="main.py",
        content="print('new')\n",
    )

    preview_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/preview",
        json={"mount_id": mount["id"], "target_path": "src/main.py"},
        headers=_auth_headers(fake_user),
    )
    assert preview_resp.status_code == 200
    preview_hash = preview_resp.json()["report"]["target_fingerprint"]["sha256"]

    target.write_text("print('external change')\n", encoding="utf-8")
    apply_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/apply",
        json={
            "mount_id": mount["id"],
            "target_path": "src/main.py",
            "confirm_write": True,
            "expected_target_hash": preview_hash,
        },
        headers=_auth_headers(fake_user),
    )

    assert apply_resp.status_code == 409
    assert apply_resp.json()["detail"] == "Target file changed since preview"
    assert target.read_text(encoding="utf-8") == "print('external change')\n"

    delivered_artifact = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}",
        headers=_auth_headers(fake_user),
    ).json()
    assert delivered_artifact["delivery_status"] == "failed"
    assert delivered_artifact["delivery_target_path"] == "src/main.py"
    assert delivered_artifact["delivery_report"]["error_code"] == "target_changed"
    assert delivered_artifact["delivery_report"]["phase"] == "consistency_check"
    assert delivered_artifact["delivery_report"]["target_fingerprint"]["sha256"] != preview_hash

    audits = await _delivery_audits(db_session, artifact["id"])
    actions = [audit.action for audit in audits]
    assert "delivery.preview.succeeded" in actions
    assert "delivery.apply.conflict" in actions
    conflict = next(audit for audit in audits if audit.action == "delivery.apply.conflict")
    assert conflict.details["artifact_id"] == artifact["id"]
    assert conflict.details["target_path"] == "src/main.py"
    assert conflict.details["expected_target_hash"] == preview_hash


async def test_delivery_apply_bridge_failure_persists_failed_report_and_audit(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    db_session: AsyncSession,
):
    root = tmp_path / "shop-api"
    root.mkdir()
    project = _create_project(async_client, fake_user, "失败交付项目")
    mount = _create_mount(async_client, fake_user, project["id"], root)
    artifact = _create_artifact(
        async_client,
        fake_user,
        project["id"],
        name="secret",
        content="SHOULD_NOT_WRITE=1\n",
    )

    denied_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/apply",
        json={"mount_id": mount["id"], "target_path": ".env", "confirm_write": True},
        headers=_auth_headers(fake_user),
    )

    assert denied_resp.status_code == 403
    assert not (root / ".env").exists()

    delivered_artifact = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}",
        headers=_auth_headers(fake_user),
    ).json()
    assert delivered_artifact["delivery_status"] == "failed"
    assert delivered_artifact["delivery_target_path"] == ".env"
    assert delivered_artifact["delivery_report"]["error_code"] == "bridge_access_error"
    assert delivered_artifact["delivery_report"]["phase"] == "apply"
    assert "Sensitive files cannot be" in delivered_artifact["delivery_report"]["error_message"]

    audits = await _delivery_audits(db_session, artifact["id"])
    assert "delivery.apply.failed" in [audit.action for audit in audits]
    failed = next(audit for audit in audits if audit.action == "delivery.apply.failed")
    assert failed.details["artifact_id"] == artifact["id"]
    assert failed.details["target_path"] == ".env"
    assert failed.details["error_code"] == "bridge_access_error"


def test_delivery_apply_rejects_unsafe_target_paths(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "shop-api"
    root.mkdir()
    project = async_client.post(
        "/api/v1/projects",
        json={"name": "安全交付项目"},
        headers=_auth_headers(fake_user),
    ).json()
    mount = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts",
        json={
            "mount_type": "local",
            "display_name": "shop-api",
            "locator": str(root),
            "role": "primary",
            "status": "connected",
        },
        headers=_auth_headers(fake_user),
    ).json()
    artifact = async_client.post(
        f"/api/v1/projects/{project['id']}/artifacts",
        json={
            "artifact_type": "code",
            "name": "secret",
            "content": "SHOULD_NOT_WRITE=1\n",
            "file_type": "text",
        },
        headers=_auth_headers(fake_user),
    ).json()

    traversal_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/apply",
        json={"mount_id": mount["id"], "target_path": "../outside.py", "confirm_write": True},
        headers=_auth_headers(fake_user),
    )
    assert traversal_resp.status_code == 400

    sensitive_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/apply",
        json={"mount_id": mount["id"], "target_path": ".env", "confirm_write": True},
        headers=_auth_headers(fake_user),
    )
    assert sensitive_resp.status_code == 403
    assert not (root / ".env").exists()


async def test_delivery_apply_without_confirmation_is_audited(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    db_session: AsyncSession,
):
    root = tmp_path / "shop-api"
    root.mkdir()
    project = _create_project(async_client, fake_user, "确认交付项目")
    mount = _create_mount(async_client, fake_user, project["id"], root)
    artifact = _create_artifact(
        async_client,
        fake_user,
        project["id"],
        name="main.py",
        content="print('new')\n",
    )

    blocked_resp = async_client.post(
        f"/api/v1/artifacts/{artifact['id']}/delivery/apply",
        json={"mount_id": mount["id"], "target_path": "src/main.py", "confirm_write": False},
        headers=_auth_headers(fake_user),
    )

    assert blocked_resp.status_code == 409
    audits = await _delivery_audits(db_session, artifact["id"])
    assert "delivery.apply.denied" in [audit.action for audit in audits]
    denied = next(audit for audit in audits if audit.action == "delivery.apply.denied")
    assert denied.details["artifact_id"] == artifact["id"]
    assert denied.details["target_path"] == "src/main.py"
    assert denied.details["reason"] == "missing_confirmation"


def _create_project(async_client: TestClient, fake_user: User, name: str) -> dict:
    return async_client.post(
        "/api/v1/projects",
        json={"name": name},
        headers=_auth_headers(fake_user),
    ).json()


def _create_mount(async_client: TestClient, fake_user: User, project_id: str, root: Path) -> dict:
    return async_client.post(
        f"/api/v1/projects/{project_id}/mounts",
        json={
            "mount_type": "local",
            "display_name": root.name,
            "locator": str(root),
            "role": "primary",
            "status": "connected",
            "metadata": {"root_path": str(root)},
        },
        headers=_auth_headers(fake_user),
    ).json()


def _create_artifact(
    async_client: TestClient,
    fake_user: User,
    project_id: str,
    *,
    name: str,
    content: str,
) -> dict:
    return async_client.post(
        f"/api/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "code",
            "name": name,
            "content": content,
            "file_type": "text",
        },
        headers=_auth_headers(fake_user),
    ).json()


async def _delivery_audits(db_session: AsyncSession, artifact_id: str) -> list[AuditLog]:
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.resource == "artifact_delivery")
        .where(AuditLog.details["artifact_id"].as_string() == artifact_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(result.scalars().all())
