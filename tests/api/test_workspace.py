"""WorkspaceExecutor API tests."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import Project, ProjectMount, TaskGraph, TaskNode, User
from agent_forge.models.session import Session
from agent_forge.pipeline.service import create_pipeline_run_for_session


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


async def _seed_api_node(
    db: AsyncSession,
    user: User,
    root: Path,
) -> tuple[TaskGraph, TaskNode, ProjectMount]:
    suffix = uuid.uuid4().hex[:8]
    project = Project(
        id=f"workspace-api-project-{suffix}",
        user_id=user.id,
        name="Workspace API project",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=f"workspace-api-session-{suffix}",
        user_id=user.id,
        project_id=project.id,
        title="Workspace API session",
        intent_type="new_feature",
    )
    mount = ProjectMount(
        id=f"workspace-api-mount-{suffix}",
        project_id=project.id,
        mount_type="local",
        display_name="workspace",
        locator=str(root),
        role="primary",
        status="connected",
        metadata_json={"root_path": str(root)},
    )
    db.add_all([project, session, mount])
    await db.flush()
    run = await create_pipeline_run_for_session(db, session, "new_feature")
    task_split = next(stage for stage in run.stages if stage.stage_id == "task_split")
    graph = TaskGraph(
        id=f"workspace-api-graph-{suffix}",
        project_id=project.id,
        pipeline_run_id=run.id,
        source_stage_state_id=task_split.id,
        schema_version=1,
        status="ready",
        summary="实现通知设置",
    )
    node = TaskNode(
        id=f"workspace-api-node-{suffix}",
        task_graph=graph,
        node_key="backend-api",
        title="实现通知 API",
        description="新增通知设置接口",
        order_index=0,
        status="pending",
        acceptance_criteria=["接口测试通过"],
        target_files=["src/api.py"],
        verification_commands=["pytest -q tests/api/test_notifications.py"],
    )
    db.add_all([graph, node])
    await db.commit()
    return graph, node, mount


async def test_workspace_preview_and_get_are_user_isolated(
    async_client: TestClient,
    db_session: AsyncSession,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    (root / "src" / "api.py").write_text("print('old')\n", encoding="utf-8")
    graph, node, mount = await _seed_api_node(db_session, fake_user, root)

    preview_response = async_client.post(
        f"/api/v1/task-graphs/{graph.id}/nodes/{node.node_key}/workspace/preview",
        json={
            "mount_id": mount.id,
            "files": [{"path": "src/api.py", "content": "print('new')\n"}],
        },
        headers=_auth_headers(fake_user),
    )

    assert preview_response.status_code == 201
    preview = preview_response.json()
    assert preview["project_id"] == graph.project_id
    assert preview["task_graph_id"] == graph.id
    assert preview["task_node_id"] == node.id
    assert preview["patches"][0]["target_path"] == "src/api.py"
    assert "proposed_content" not in preview["patches"][0]
    assert (root / "src" / "api.py").read_text(encoding="utf-8") == "print('old')\n"

    get_response = async_client.get(
        f"/api/v1/workspace-change-sets/{preview['id']}",
        headers=_auth_headers(fake_user),
    )
    assert get_response.status_code == 200
    assert get_response.json() == preview

    other_root = tmp_path / "other-workspace"
    other_root.mkdir()
    _other_graph, _other_node, other_mount = await _seed_api_node(
        db_session,
        fake_user,
        other_root,
    )
    cross_project_response = async_client.post(
        f"/api/v1/task-graphs/{graph.id}/nodes/{node.node_key}/workspace/preview",
        json={
            "mount_id": other_mount.id,
            "files": [{"path": "src/api.py", "content": "print('cross')\n"}],
        },
        headers=_auth_headers(fake_user),
    )
    assert cross_project_response.status_code == 404

    foreign_user = User(
        id=f"workspace-api-foreign-{uuid.uuid4().hex[:8]}",
        username=f"workspace-api-foreign-{uuid.uuid4().hex[:8]}",
        email=f"workspace-api-foreign-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="not-used",
        permissions=["read"],
    )
    db_session.add(foreign_user)
    await db_session.commit()
    foreign_root = tmp_path / "foreign-workspace"
    foreign_root.mkdir()
    foreign_graph, foreign_node, foreign_mount = await _seed_api_node(
        db_session,
        foreign_user,
        foreign_root,
    )

    foreign_preview_response = async_client.post(
        f"/api/v1/task-graphs/{foreign_graph.id}/nodes/{foreign_node.node_key}/workspace/preview",
        json={
            "mount_id": foreign_mount.id,
            "files": [{"path": "src/api.py", "content": "print('foreign')\n"}],
        },
        headers=_auth_headers(fake_user),
    )
    assert foreign_preview_response.status_code == 404
