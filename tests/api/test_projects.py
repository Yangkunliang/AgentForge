"""Project / Mount / Artifact API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import User


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


def test_create_project_and_project_session(async_client: TestClient, fake_user: User):
    resp = async_client.post(
        "/api/v1/projects",
        json={
            "name": "我的电商后端",
            "description": "FastAPI + Vue 3 电商项目",
            "tech_tags": ["FastAPI", "Vue 3", "PostgreSQL"],
        },
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 201
    project = resp.json()
    assert project["name"] == "我的电商后端"
    assert project["display_name"] == "我的电商后端"
    assert project["tech_tags"] == ["FastAPI", "Vue 3", "PostgreSQL"]
    assert project["status"] == "active"

    session_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/sessions",
        json={"title": "设计订单退款流程", "intent_type": "new_feature"},
        headers=_auth_headers(fake_user),
    )

    assert session_resp.status_code == 201
    session = session_resp.json()
    assert session["project_id"] == project["id"]
    assert session["title"] == "设计订单退款流程"
    assert session["intent_type"] == "new_feature"
    assert session["current_pipeline_run_id"] is None

    list_resp = async_client.get(
        f"/api/v1/projects/{project['id']}/sessions",
        headers=_auth_headers(fake_user),
    )
    assert list_resp.status_code == 200
    assert [item["id"] for item in list_resp.json()] == [session["id"]]


def test_legacy_create_session_assigns_default_project(async_client: TestClient, fake_user: User):
    resp = async_client.post(
        "/api/v1/sessions",
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 201
    session = resp.json()
    assert session["project_id"]
    assert session["intent_type"] is None

    project_resp = async_client.get(
        f"/api/v1/projects/{session['project_id']}",
        headers=_auth_headers(fake_user),
    )
    assert project_resp.status_code == 200
    assert project_resp.json()["name"] == "默认项目"


def test_project_mounts_support_local_github_and_upload(async_client: TestClient, fake_user: User):
    project = async_client.post(
        "/api/v1/projects",
        json={"name": "多目录项目"},
        headers=_auth_headers(fake_user),
    ).json()

    payloads = [
        {
            "mount_type": "local",
            "display_name": "shop-api",
            "locator": "/Users/me/work/shop-api",
            "role": "primary",
        },
        {
            "mount_type": "github",
            "display_name": "shop-web",
            "locator": "https://github.com/acme/shop-web",
            "role": "reference",
        },
        {
            "mount_type": "upload",
            "display_name": "需求文档包",
            "locator": "upload://bundle-001",
            "role": "docs",
        },
    ]

    for payload in payloads:
        resp = async_client.post(
            f"/api/v1/projects/{project['id']}/mounts",
            json=payload,
            headers=_auth_headers(fake_user),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["project_id"] == project["id"]
        assert data["mount_type"] == payload["mount_type"]
        assert data["role"] == payload["role"]
        assert data["status"] == "pending"

    list_resp = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts",
        headers=_auth_headers(fake_user),
    )
    assert list_resp.status_code == 200
    assert [item["mount_type"] for item in list_resp.json()] == ["local", "github", "upload"]


def test_artifact_is_saved_under_project_and_session(async_client: TestClient, fake_user: User):
    project = async_client.post(
        "/api/v1/projects",
        json={"name": "产物归档项目"},
        headers=_auth_headers(fake_user),
    ).json()
    session = async_client.post(
        f"/api/v1/projects/{project['id']}/sessions",
        json={"title": "生成 PRD", "intent_type": "iteration"},
        headers=_auth_headers(fake_user),
    ).json()

    resp = async_client.post(
        f"/api/v1/projects/{project['id']}/artifacts",
        json={
            "session_id": session["id"],
            "artifact_type": "prd",
            "name": "PRODUCT-REQUIREMENTS.md",
            "content": "# 退款流程优化",
            "file_type": "markdown",
            "metadata": {"stage": "requirements"},
        },
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 201
    artifact = resp.json()
    assert artifact["project_id"] == project["id"]
    assert artifact["session_id"] == session["id"]
    assert artifact["artifact_type"] == "prd"
    assert artifact["content"] == "# 退款流程优化"
    assert artifact["metadata"] == {"stage": "requirements"}

    get_resp = async_client.get(
        f"/api/v1/artifacts/{artifact['id']}",
        headers=_auth_headers(fake_user),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == artifact["id"]


async def test_project_access_is_scoped_to_current_user(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
):
    project = async_client.post(
        "/api/v1/projects",
        json={"name": "别人的项目"},
        headers=_auth_headers(fake_user),
    ).json()

    await db_session.execute(
        text("UPDATE projects SET user_id = 'other-user' WHERE id = :project_id"),
        {"project_id": project["id"]},
    )
    await db_session.commit()

    get_resp = async_client.get(
        f"/api/v1/projects/{project['id']}",
        headers=_auth_headers(fake_user),
    )
    assert get_resp.status_code == 404

    mount_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts",
        json={
            "mount_type": "local",
            "display_name": "other",
            "locator": "/tmp/other",
            "role": "primary",
        },
        headers=_auth_headers(fake_user),
    )
    assert mount_resp.status_code == 404
