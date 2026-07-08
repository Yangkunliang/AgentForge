"""Delivery API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import User


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
