"""Pipeline Catalog API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import User


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
    assert analysis["default_agent_selector"] == "planner"
    assert analysis["model_route_key"] == "default"
    assert analysis["skill_policy_key"] == "default"


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
    assert stage_by_id["backend_dev"]["output_artifact_types"] == ["code"]

    missing = async_client.get(
        "/api/v1/pipeline/catalog/not_real",
        headers=_auth_headers(fake_user),
    )
    assert missing.status_code == 404
