"""WorkspaceExecutor preview service tests."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.bridge.files import BridgeAccessError
from agent_forge.models import Project, ProjectMount, TaskGraph, TaskNode, User, WorkspaceChangeSet
from agent_forge.models.session import Session
from agent_forge.pipeline.service import create_pipeline_run_for_session
from agent_forge.workspace import (
    FileProposal,
    WorkspaceExecutionError,
    apply_workspace_change_set,
    create_workspace_preview,
    load_workspace_change_set_for_user,
    workspace_change_set_to_dict,
)
from agent_forge.workspace import service as workspace_service


async def _seed_workspace_node(
    db: AsyncSession,
    user: User,
    root: Path,
    *,
    mount_type: str = "local",
    mount_role: str = "primary",
    mount_status: str = "connected",
    target_files: list[str] | None = None,
) -> tuple[TaskGraph, TaskNode, ProjectMount]:
    suffix = uuid.uuid4().hex[:8]
    project = Project(
        id=f"workspace-project-{suffix}",
        user_id=user.id,
        name="Workspace project",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=f"workspace-session-{suffix}",
        user_id=user.id,
        project_id=project.id,
        title="Workspace session",
        intent_type="new_feature",
    )
    mount = ProjectMount(
        id=f"workspace-mount-{suffix}",
        project_id=project.id,
        mount_type=mount_type,
        display_name="workspace",
        locator=str(root),
        role=mount_role,
        status=mount_status,
        metadata_json={"root_path": str(root)},
    )
    db.add_all([project, session, mount])
    await db.flush()
    run = await create_pipeline_run_for_session(db, session, "new_feature")
    task_split = next(stage for stage in run.stages if stage.stage_id == "task_split")
    graph = TaskGraph(
        id=f"workspace-graph-{suffix}",
        project_id=project.id,
        pipeline_run_id=run.id,
        source_stage_state_id=task_split.id,
        schema_version=1,
        status="ready",
        summary="实现通知设置",
    )
    node = TaskNode(
        id=f"workspace-node-{suffix}",
        task_graph=graph,
        node_key="backend-api",
        title="实现通知 API",
        description="新增通知设置接口",
        order_index=0,
        status="pending",
        acceptance_criteria=["接口测试通过"],
        target_files=(
            target_files
            if target_files is not None
            else ["src/api.py", "src/new_file.py"]
        ),
        verification_commands=["pytest -q tests/api/test_notifications.py"],
    )
    db.add_all([graph, node])
    await db.commit()
    return graph, node, mount


@pytest.mark.asyncio
async def test_preview_persists_multi_file_patches_without_writing(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    existing = root / "src" / "api.py"
    existing.write_text("print('old')\n", encoding="utf-8")
    graph, node, mount = await _seed_workspace_node(db, fake_user, root)

    change_set = await create_workspace_preview(
        db,
        user_id=fake_user.id,
        graph_id=graph.id,
        node_key=node.node_key,
        mount_id=mount.id,
        proposals=[
            FileProposal(path="src/api.py", content="print('new')\n"),
            FileProposal(path="src/new_file.py", content="ENABLED = True\n"),
        ],
    )
    await db.commit()

    assert isinstance(change_set, WorkspaceChangeSet)
    payload = workspace_change_set_to_dict(change_set)
    assert payload["status"] == "previewed"
    assert payload["task_graph_id"] == graph.id
    assert payload["task_node_id"] == node.id
    assert payload["mount_id"] == mount.id
    assert payload["has_changes"] is True
    assert [patch["target_path"] for patch in payload["patches"]] == [
        "src/api.py",
        "src/new_file.py",
    ]
    assert payload["patches"][0]["base_fingerprint"]["exists"] is True
    assert payload["patches"][0]["base_fingerprint"]["sha256"]
    assert "-print('old')" in payload["patches"][0]["unified_diff"]
    assert "+print('new')" in payload["patches"][0]["unified_diff"]
    assert payload["patches"][1]["base_fingerprint"] == {
        "exists": False,
        "size": 0,
        "sha256": None,
    }
    assert existing.read_text(encoding="utf-8") == "print('old')\n"
    assert not (root / "src" / "new_file.py").exists()


@pytest.mark.asyncio
async def test_preview_rejects_path_not_declared_by_task_node(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    root.mkdir()
    graph, node, mount = await _seed_workspace_node(db, fake_user, root)

    with pytest.raises(WorkspaceExecutionError, match="not declared") as exc_info:
        await create_workspace_preview(
            db,
            user_id=fake_user.id,
            graph_id=graph.id,
            node_key=node.node_key,
            mount_id=mount.id,
            proposals=[FileProposal(path="src/undeclared.py", content="unsafe = True\n")],
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "path_not_declared"


@pytest.mark.asyncio
async def test_preview_failure_does_not_commit_partial_change_set(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    (root / "src" / "directory").mkdir(parents=True)
    (root / "src" / "api.py").write_text("print('old')\n", encoding="utf-8")
    graph, node, mount = await _seed_workspace_node(
        db,
        fake_user,
        root,
        target_files=["src/api.py", "src/directory"],
    )

    with pytest.raises(WorkspaceExecutionError, match="must be a file"):
        await create_workspace_preview(
            db,
            user_id=fake_user.id,
            graph_id=graph.id,
            node_key=node.node_key,
            mount_id=mount.id,
            proposals=[
                FileProposal(path="src/api.py", content="print('new')\n"),
                FileProposal(path="src/directory", content="not-a-file\n"),
            ],
        )
    await db.commit()

    persisted = await db.scalars(
        select(WorkspaceChangeSet).where(
            WorkspaceChangeSet.task_node_id == node.id
        )
    )
    assert persisted.all() == []


@pytest.mark.asyncio
async def test_preview_rejects_duplicate_and_sensitive_paths(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    root.mkdir()
    graph, node, mount = await _seed_workspace_node(db, fake_user, root)

    with pytest.raises(WorkspaceExecutionError) as duplicate_error:
        await create_workspace_preview(
            db,
            user_id=fake_user.id,
            graph_id=graph.id,
            node_key=node.node_key,
            mount_id=mount.id,
            proposals=[
                FileProposal(path="src/api.py", content="first\n"),
                FileProposal(path="src/api.py", content="second\n"),
            ],
        )
    assert duplicate_error.value.error_code == "duplicate_path"

    node.target_files = [".env"]
    await db.commit()
    with pytest.raises(WorkspaceExecutionError) as sensitive_error:
        await create_workspace_preview(
            db,
            user_id=fake_user.id,
            graph_id=graph.id,
            node_key=node.node_key,
            mount_id=mount.id,
            proposals=[FileProposal(path=".env", content="SECRET=1\n")],
        )
    assert sensitive_error.value.status_code == 403
    assert sensitive_error.value.error_code == "bridge_access_error"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mount_type", "mount_status", "mount_role"),
    [
        ("github", "connected", "primary"),
        ("local", "disconnected", "primary"),
        ("local", "connected", "reference"),
    ],
)
async def test_preview_rejects_non_writable_mount(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
    mount_type: str,
    mount_status: str,
    mount_role: str,
):
    root = tmp_path / "workspace"
    root.mkdir()
    graph, node, mount = await _seed_workspace_node(
        db,
        fake_user,
        root,
        mount_type=mount_type,
        mount_status=mount_status,
        mount_role=mount_role,
    )

    with pytest.raises(WorkspaceExecutionError, match="primary") as exc_info:
        await create_workspace_preview(
            db,
            user_id=fake_user.id,
            graph_id=graph.id,
            node_key=node.node_key,
            mount_id=mount.id,
            proposals=[FileProposal(path="src/api.py", content="print('new')\n")],
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "mount_not_writable"


@pytest.mark.asyncio
async def test_apply_writes_all_changed_files_and_is_idempotent(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    existing = root / "src" / "api.py"
    existing.write_text("print('old')\n", encoding="utf-8")
    graph, node, mount = await _seed_workspace_node(db, fake_user, root)
    change_set = await create_workspace_preview(
        db,
        user_id=fake_user.id,
        graph_id=graph.id,
        node_key=node.node_key,
        mount_id=mount.id,
        proposals=[
            FileProposal(path="src/api.py", content="print('new')\n"),
            FileProposal(path="src/new_file.py", content="ENABLED = True\n"),
        ],
    )
    await db.commit()

    applied = await apply_workspace_change_set(db, change_set=change_set)
    await db.commit()

    payload = workspace_change_set_to_dict(applied)
    assert payload["status"] == "applied"
    assert [patch["status"] for patch in payload["patches"]] == [
        "applied",
        "applied",
    ]
    assert payload["apply_report"]["status"] == "applied"
    assert payload["apply_report"]["file_count"] == 2
    assert payload["apply_report"]["changed_count"] == 2
    assert "proposed_content" not in str(payload["apply_report"])
    assert existing.read_text(encoding="utf-8") == "print('new')\n"
    assert (root / "src" / "new_file.py").read_text(encoding="utf-8") == (
        "ENABLED = True\n"
    )

    def _unexpected_write(*_args, **_kwargs):
        raise AssertionError("idempotent apply must not write files")

    monkeypatch.setattr(workspace_service, "write_mount_file", _unexpected_write)
    retried = await apply_workspace_change_set(db, change_set=applied)
    assert retried.apply_report_json == applied.apply_report_json


@pytest.mark.asyncio
async def test_apply_loader_locks_only_the_change_set_row():
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    expected = MagicMock(spec=WorkspaceChangeSet)
    result.unique.return_value.scalar_one_or_none.return_value = expected
    db.execute.return_value = result

    loaded = await load_workspace_change_set_for_user(
        db,
        change_set_id="change-set-1",
        user_id="user-1",
        for_update=True,
    )

    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE OF workspace_change_sets" in sql
    assert loaded is expected


@pytest.mark.asyncio
async def test_apply_rechecks_all_baselines_before_writing(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    existing = root / "src" / "api.py"
    existing.write_text("print('old')\n", encoding="utf-8")
    graph, node, mount = await _seed_workspace_node(db, fake_user, root)
    change_set = await create_workspace_preview(
        db,
        user_id=fake_user.id,
        graph_id=graph.id,
        node_key=node.node_key,
        mount_id=mount.id,
        proposals=[
            FileProposal(path="src/api.py", content="print('new')\n"),
            FileProposal(path="src/new_file.py", content="ENABLED = True\n"),
        ],
    )
    await db.commit()
    external = root / "src" / "new_file.py"
    external.write_text("EXTERNAL = True\n", encoding="utf-8")

    with pytest.raises(
        WorkspaceExecutionError,
        match="changed since preview",
    ) as exc_info:
        await apply_workspace_change_set(db, change_set=change_set)
    await db.commit()

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "baseline_changed"
    assert existing.read_text(encoding="utf-8") == "print('old')\n"
    assert external.read_text(encoding="utf-8") == "EXTERNAL = True\n"
    assert change_set.status == "failed"
    assert change_set.apply_report_json["phase"] == "consistency_check"


@pytest.mark.asyncio
async def test_apply_rejects_mount_root_changed_after_preview(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
):
    original_root = tmp_path / "original-workspace"
    changed_root = tmp_path / "changed-workspace"
    original_root.mkdir()
    changed_root.mkdir()
    graph, node, mount = await _seed_workspace_node(
        db,
        fake_user,
        original_root,
        target_files=["src/new_file.py"],
    )
    change_set = await create_workspace_preview(
        db,
        user_id=fake_user.id,
        graph_id=graph.id,
        node_key=node.node_key,
        mount_id=mount.id,
        proposals=[FileProposal(path="src/new_file.py", content="ENABLED = True\n")],
    )
    await db.commit()
    mount.metadata_json = {"root_path": str(changed_root)}
    await db.commit()

    with pytest.raises(WorkspaceExecutionError) as exc_info:
        await apply_workspace_change_set(db, change_set=change_set)

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "mount_authorization_changed"
    assert not (original_root / "src" / "new_file.py").exists()
    assert not (changed_root / "src" / "new_file.py").exists()


@pytest.mark.asyncio
async def test_apply_rejects_mount_revoked_after_preview(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    root.mkdir()
    graph, node, mount = await _seed_workspace_node(db, fake_user, root)
    change_set = await create_workspace_preview(
        db,
        user_id=fake_user.id,
        graph_id=graph.id,
        node_key=node.node_key,
        mount_id=mount.id,
        proposals=[FileProposal(path="src/api.py", content="print('new')\n")],
    )
    await db.commit()
    mount.status = "disconnected"
    await db.commit()

    with pytest.raises(WorkspaceExecutionError) as exc_info:
        await apply_workspace_change_set(db, change_set=change_set)

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "mount_not_writable"
    assert not (root / "src" / "api.py").exists()


@pytest.mark.asyncio
async def test_apply_rolls_back_files_written_before_failure(
    db: AsyncSession,
    fake_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    existing = root / "src" / "api.py"
    existing.write_text("print('old')\n", encoding="utf-8")
    graph, node, mount = await _seed_workspace_node(db, fake_user, root)
    change_set = await create_workspace_preview(
        db,
        user_id=fake_user.id,
        graph_id=graph.id,
        node_key=node.node_key,
        mount_id=mount.id,
        proposals=[
            FileProposal(path="src/api.py", content="print('new')\n"),
            FileProposal(path="src/new_file.py", content="ENABLED = True\n"),
        ],
    )
    await db.commit()
    real_write = workspace_service.write_mount_file
    write_count = 0

    def _fail_second_write(mount, path, content):
        nonlocal write_count
        write_count += 1
        if write_count == 2:
            raise BridgeAccessError(500, "simulated second write failure")
        return real_write(mount, path, content)

    monkeypatch.setattr(workspace_service, "write_mount_file", _fail_second_write)

    with pytest.raises(WorkspaceExecutionError, match="simulated") as exc_info:
        await apply_workspace_change_set(db, change_set=change_set)
    await db.commit()

    assert exc_info.value.error_code == "bridge_access_error"
    assert existing.read_text(encoding="utf-8") == "print('old')\n"
    assert not (root / "src" / "new_file.py").exists()
    assert change_set.status == "failed"
    assert change_set.apply_report_json["rollback"] == {
        "attempted": True,
        "succeeded": True,
        "paths": ["src/new_file.py", "src/api.py"],
        "errors": [],
    }

    with pytest.raises(WorkspaceExecutionError) as retry_error:
        await apply_workspace_change_set(db, change_set=change_set)
    assert retry_error.value.error_code == "change_set_failed"
