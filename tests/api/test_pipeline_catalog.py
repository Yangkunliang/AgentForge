"""Pipeline Catalog API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import User
from agent_forge.pipeline.catalog import ARTIFACT_TYPES, list_pipeline_definitions


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


def test_pipeline_catalog_lists_all_intent_stage_definitions(
    async_client: TestClient,
    fake_user: User,
):
    resp = async_client.get(
        "/api/v1/pipeline/catalog",
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert [item["intent_type"] for item in body["items"]] == [
        "new_feature",
        "iteration",
        "ui_adjust",
        "bug_fix",
    ]

    new_feature = body["items"][0]
    assert new_feature["label"] == "全新功能"
    assert new_feature["default_actions"][0]["id"] == "define_scope"
    assert [stage["stage_id"] for stage in new_feature["stages"]] == [
        "analysis",
        "design",
        "db_api",
        "task_split",
        "ui_prototype",
        "backend_dev",
        "frontend_dev",
        "testing",
    ]

    analysis = new_feature["stages"][0]
    assert analysis["stage_name"] == "需求分析"
    assert analysis["order_index"] == 0
    assert analysis["required"] is True
    assert analysis["can_skip"] is False
    assert analysis["can_restore"] is False
    assert analysis["confirmation_required"] is True
    assert analysis["confirmation_policy"] == {
        "required": True,
        "type": "stage_output",
        "gate": "prd_review",
    }
    assert analysis["output_artifact_types"] == ["prd"]
    assert analysis["required_input_artifact_types"] == []
    assert analysis["success_criteria"] == [
        "明确用户目标与角色。",
        "列出范围、非目标和验收标准。",
    ]
    assert analysis["default_agent_selector"] == "planner"
    assert analysis["model_route_key"] == "default"
    assert analysis["skill_policy_key"] == "default"

    stage_by_id = {stage["stage_id"]: stage for stage in new_feature["stages"]}
    assert stage_by_id["design"]["required_input_artifact_types"] == ["prd"]
    assert stage_by_id["backend_dev"]["required_input_artifact_types"] == [
        "prd",
        "architecture",
        "api_spec",
        "report",
    ]
    assert stage_by_id["backend_dev"]["success_criteria"] == [
        "实现后端与自动化测试。",
        "说明改动文件和回归结果。",
    ]
    assert stage_by_id["testing"]["required_input_artifact_types"] == ["prd", "code"]
    assert all(stage["success_criteria"] for stage in new_feature["stages"])


def test_pipeline_catalog_gets_single_intent_and_rejects_unknown_intent(
    async_client: TestClient,
    fake_user: User,
):
    resp = async_client.get(
        "/api/v1/pipeline/catalog/iteration",
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["intent_type"] == "iteration"
    assert body["label"] == "迭代优化"
    stage_by_id = {stage["stage_id"]: stage for stage in body["stages"]}
    assert stage_by_id["impact"]["required"] is False
    assert stage_by_id["impact"]["can_skip"] is True
    assert stage_by_id["impact"]["can_restore"] is True
    assert stage_by_id["impact"]["confirmation_policy"]["gate"] == "impact_review"
    assert stage_by_id["impact"]["required_input_artifact_types"] == ["diff"]
    assert stage_by_id["backend_dev"]["output_artifact_types"] == ["code"]
    assert stage_by_id["regression"]["success_criteria"] == [
        "执行变更点和相关回归。",
        "记录失败与残余风险。",
    ]

    missing = async_client.get(
        "/api/v1/pipeline/catalog/not_real",
        headers=_auth_headers(fake_user),
    )
    assert missing.status_code == 404


def test_pipeline_catalog_defines_every_stage_artifact_type():
    catalog_types = {
        artifact_type
        for pipeline in list_pipeline_definitions()
        for stage in pipeline.stages
        for artifact_type in (
            *stage.required_input_artifact_types,
            *stage.output_artifact_types,
        )
    }

    assert catalog_types == ARTIFACT_TYPES
