"""Project / Mount / Artifact API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import Artifact, User
from agent_forge.models.session import Message


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


def test_connected_local_mount_lists_and_reads_files_inside_authorized_root(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "shop-api"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.py").write_text("print('hello from mounted repo')\n", encoding="utf-8")
    (src_dir / ".env").write_text("DATABASE_URL=postgres://secret\n", encoding="utf-8")

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "授权代码库"},
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

    status_resp = async_client.get(
        f"/api/v1/projects/{project['id']}/bridge/status",
        headers=_auth_headers(fake_user),
    )
    assert status_resp.status_code == 200
    bridge_status = status_resp.json()
    assert bridge_status["connected_mounts"] == 1
    assert bridge_status["mounts"][0]["mount_id"] == mount["id"]
    assert bridge_status["mounts"][0]["root_path"] == str(root.resolve())

    list_resp = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files",
        params={"path": "src"},
        headers=_auth_headers(fake_user),
    )
    assert list_resp.status_code == 200
    files = list_resp.json()["entries"]
    assert [item["relative_path"] for item in files] == ["src/main.py"]

    read_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files/read",
        json={"path": "src/main.py"},
        headers=_auth_headers(fake_user),
    )
    assert read_resp.status_code == 200
    content = read_resp.json()
    assert content["mount_id"] == mount["id"]
    assert content["path"] == "src/main.py"
    assert content["content"] == "print('hello from mounted repo')\n"
    assert content["truncated"] is False

    traversal_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files/read",
        json={"path": "../outside.py"},
        headers=_auth_headers(fake_user),
    )
    assert traversal_resp.status_code == 400

    sensitive_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files/read",
        json={"path": "src/.env"},
        headers=_auth_headers(fake_user),
    )
    assert sensitive_resp.status_code == 403


def test_mount_file_read_requires_connected_local_mount(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "shop-api"
    root.mkdir()
    (root / "main.py").write_text("print('not connected')\n", encoding="utf-8")

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "未连接代码库"},
        headers=_auth_headers(fake_user),
    ).json()
    mount = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts",
        json={
            "mount_type": "local",
            "display_name": "shop-api",
            "locator": str(root),
            "role": "primary",
            "status": "disconnected",
        },
        headers=_auth_headers(fake_user),
    ).json()

    read_resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}/files/read",
        json={"path": "main.py"},
        headers=_auth_headers(fake_user),
    )
    assert read_resp.status_code == 409


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


async def test_session_messages_include_linked_artifacts(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
):
    project = async_client.post(
        "/api/v1/projects",
        json={"name": "消息产物项目"},
        headers=_auth_headers(fake_user),
    ).json()
    session = async_client.post(
        f"/api/v1/projects/{project['id']}/sessions",
        json={"title": "生成技术方案", "intent_type": "new_feature"},
        headers=_auth_headers(fake_user),
    ).json()

    assistant_msg = Message(
        id="msg-with-artifact",
        session_id=session["id"],
        role="assistant",
        content="已经生成技术方案",
        task_id=None,
    )
    artifact = Artifact(
        id="artifact-tech-design",
        project_id=project["id"],
        session_id=session["id"],
        pipeline_run_id="run-design",
        stage_state_id="stage-design",
        artifact_type="architecture",
        name="架构设计.md",
        content="# 架构设计",
        file_type="markdown",
        source_message_id=assistant_msg.id,
        metadata_json={"stage_id": "design"},
    )
    db_session.add_all([assistant_msg, artifact])
    await db_session.commit()

    resp = async_client.get(
        f"/api/v1/sessions/{session['id']}/messages",
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 200
    [message] = resp.json()
    assert message["id"] == assistant_msg.id
    [linked_artifact] = message["artifacts"]
    assert linked_artifact | {
        "created_at": None,
        "updated_at": None,
    } == {
        "id": "artifact-tech-design",
        "project_id": project["id"],
        "session_id": session["id"],
        "pipeline_run_id": "run-design",
        "stage_state_id": "stage-design",
        "artifact_type": "architecture",
        "name": "架构设计.md",
        "content": "# 架构设计",
        "file_type": "markdown",
        "source_message_id": "msg-with-artifact",
        "metadata": {"stage_id": "design"},
        "created_at": None,
        "updated_at": None,
    }
    assert linked_artifact["created_at"]
    assert linked_artifact["updated_at"]


def test_chat_context_hydrates_selected_mount_file_content(
    async_client: TestClient,
    fake_user: User,
    tmp_path: Path,
    monkeypatch,
):
    root = tmp_path / "shop-api"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.py").write_text("def checkout():\n    return 'ok'\n", encoding="utf-8")

    captured: dict = {}

    def capture_run_task_with_skills(**kwargs):
        captured.update(kwargs)

        async def noop():
            return None

        return noop()

    monkeypatch.setattr("api.routes.sessions._run_task_with_skills", capture_run_task_with_skills)

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "上下文注入项目"},
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
    session = async_client.post(
        f"/api/v1/projects/{project['id']}/sessions",
        json={"title": "读取真实文件", "intent_type": "iteration"},
        headers=_auth_headers(fake_user),
    ).json()

    resp = async_client.post(
        f"/api/v1/sessions/{session['id']}/chat",
        json={
            "content": "基于 main.py 看一下 checkout",
            "intent": "iteration",
            "context_files": [
                {
                    "type": "file",
                    "value": "src/main.py",
                    "label": "shop-api/src/main.py",
                    "mount_id": mount["id"],
                }
            ],
        },
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 202
    [context_item] = captured["advanced_context"]["context_files"]
    assert context_item["mount_id"] == mount["id"]
    assert context_item["value"] == "src/main.py"
    assert context_item["source"] == "project_mount"
    assert context_item["content"] == "def checkout():\n    return 'ok'\n"
    assert context_item["content_truncated"] is False
