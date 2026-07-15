"""TaskGraph output contract tests."""

from __future__ import annotations

import json

import pytest

from agent_forge.pipeline.task_graph import (
    TaskGraphOutputError,
    parse_task_graph_output,
    render_task_graph_markdown,
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
