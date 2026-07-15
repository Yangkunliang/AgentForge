"""TaskGraph output contract tests."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Artifact, Project, Session, TaskGraph, User
from agent_forge.pipeline.service import create_pipeline_run_for_session
from agent_forge.pipeline.task_graph import (
    TaskGraphAlreadyExistsError,
    TaskGraphOutputError,
    create_task_graph,
    load_task_graph_for_run,
    parse_task_graph_output,
    render_task_graph_markdown,
    task_graph_to_dict,
)


def _valid_payload() -> dict:
    return {
        "summary": "实现用户通知设置",
        "nodes": [
            {
                "key": "backend-api",
                "title": "新增通知设置 API",
                "description": "实现模型、服务和路由",
                "depends_on": [],
                "acceptance_criteria": ["API 权限和错误响应符合契约"],
                "target_files": ["src/api/routes/notifications.py"],
                "verification_commands": [
                    "pytest -q tests/api/test_notifications.py"
                ],
            },
            {
                "key": "frontend-page",
                "title": "新增通知设置页面",
                "description": "实现表单和错误状态",
                "depends_on": ["backend-api"],
                "acceptance_criteria": ["保存成功和失败状态可见"],
                "target_files": ["web/src/views/settings/Notifications.vue"],
                "verification_commands": ["npm run build"],
            },
        ],
    }


def test_parse_task_graph_output_validates_dag_and_renders_markdown():
    spec = parse_task_graph_output(json.dumps(_valid_payload(), ensure_ascii=False))

    assert spec.summary == "实现用户通知设置"
    assert [node.key for node in spec.nodes] == ["backend-api", "frontend-page"]
    assert spec.nodes[1].depends_on == ["backend-api"]

    markdown = render_task_graph_markdown(spec)
    assert "# 任务图：实现用户通知设置" in markdown
    assert "## 1. 新增通知设置 API" in markdown
    assert "依赖：backend-api" in markdown
    assert "pytest -q tests/api/test_notifications.py" in markdown


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("not-json", "valid JSON"),
        (
            {**_valid_payload(), "nodes": [_valid_payload()["nodes"][0]] * 2},
            "duplicate node key",
        ),
        (
            {
                **_valid_payload(),
                "nodes": [
                    {
                        **_valid_payload()["nodes"][0],
                        "depends_on": ["missing-node"],
                    }
                ],
            },
            "unknown dependency",
        ),
        (
            {
                **_valid_payload(),
                "nodes": [
                    {
                        **_valid_payload()["nodes"][0],
                        "depends_on": ["backend-api"],
                    }
                ],
            },
            "cannot depend on itself",
        ),
        (
            {
                **_valid_payload(),
                "nodes": [
                    {**_valid_payload()["nodes"][0], "depends_on": ["frontend-page"]},
                    {**_valid_payload()["nodes"][1], "depends_on": ["backend-api"]},
                ],
            },
            "cycle",
        ),
        (
            {
                **_valid_payload(),
                "nodes": [
                    {
                        **_valid_payload()["nodes"][0],
                        "target_files": ["../secrets.env"],
                    }
                ],
            },
            "project-relative",
        ),
    ],
)
def test_parse_task_graph_output_rejects_invalid_graph(payload, message):
    raw = payload if isinstance(payload, str) else json.dumps(payload)

    with pytest.raises(TaskGraphOutputError, match=message):
        parse_task_graph_output(raw)


@pytest.mark.asyncio
async def test_create_task_graph_persists_nodes_dependencies_and_serializes_keys(
    db: AsyncSession,
    fake_user: User,
):
    suffix = uuid.uuid4().hex[:8]
    project = Project(
        id=f"task-graph-project-{suffix}",
        user_id=fake_user.id,
        name="TaskGraph project",
        tech_tags=["FastAPI", "Vue"],
        status="active",
    )
    session = Session(
        id=f"task-graph-session-{suffix}",
        user_id=fake_user.id,
        project_id=project.id,
        title="TaskGraph session",
        intent_type="new_feature",
    )
    db.add_all([project, session])
    await db.commit()
    run = await create_pipeline_run_for_session(db, session, "new_feature")
    await db.commit()
    task_split_stage = next(stage for stage in run.stages if stage.stage_id == "task_split")
    artifact = Artifact(
        id=f"task-graph-artifact-{suffix}",
        project_id=project.id,
        session_id=session.id,
        pipeline_run_id=run.id,
        stage_state_id=task_split_stage.id,
        artifact_type="report",
        name="任务拆解.md",
        content="task graph",
        file_type="markdown",
        metadata_json={"stage_id": "task_split"},
    )
    db.add(artifact)
    await db.flush()
    spec = parse_task_graph_output(json.dumps(_valid_payload()))

    graph = await create_task_graph(
        db,
        run=run,
        stage=task_split_stage,
        source_artifact=artifact,
        spec=spec,
    )
    await db.commit()

    loaded = await load_task_graph_for_run(db, run_id=run.id)
    assert isinstance(loaded, TaskGraph)
    assert loaded.id == graph.id
    payload = task_graph_to_dict(loaded)
    assert payload["project_id"] == project.id
    assert payload["pipeline_run_id"] == run.id
    assert payload["source_artifact_id"] == artifact.id
    assert payload["status"] == "ready"
    assert [node["key"] for node in payload["nodes"]] == [
        "backend-api",
        "frontend-page",
    ]
    assert payload["nodes"][1]["depends_on"] == ["backend-api"]
    assert payload["nodes"][1]["acceptance_criteria"] == [
        "保存成功和失败状态可见"
    ]

    with pytest.raises(TaskGraphAlreadyExistsError):
        await create_task_graph(
            db,
            run=run,
            stage=task_split_stage,
            source_artifact=artifact,
            spec=spec,
        )
