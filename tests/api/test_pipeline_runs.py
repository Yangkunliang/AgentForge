"""PipelineRun / StageState API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import User


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


def _create_project(async_client: TestClient, fake_user: User) -> dict:
    resp = async_client.post(
        "/api/v1/projects",
        json={"name": "状态机项目", "tech_tags": ["FastAPI", "Vue 3"]},
        headers=_auth_headers(fake_user),
    )
    assert resp.status_code == 201
    return resp.json()


def _create_project_session(
    async_client: TestClient,
    fake_user: User,
    project_id: str,
    intent_type: str = "new_feature",
) -> dict:
    resp = async_client.post(
        f"/api/v1/projects/{project_id}/sessions",
        json={"title": "实现支付渠道", "intent_type": intent_type},
        headers=_auth_headers(fake_user),
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_pipeline_run_from_intent_generates_persisted_stage_plan(
    async_client: TestClient,
    fake_user: User,
):
    project = _create_project(async_client, fake_user)
    session = _create_project_session(async_client, fake_user, project["id"], "new_feature")

    resp = async_client.post(
        f"/api/v1/sessions/{session['id']}/pipeline-runs",
        json={"intent_type": "new_feature"},
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 201
    run = resp.json()
    assert run["project_id"] == project["id"]
    assert run["session_id"] == session["id"]
    assert run["intent_type"] == "new_feature"
    assert run["status"] == "planned"
    assert run["current_stage_id"] == "analysis"
    assert [stage["stage_id"] for stage in run["stages"]] == [
        "analysis",
        "design",
        "db_api",
        "task_split",
        "ui_prototype",
        "backend_dev",
        "frontend_dev",
        "testing",
    ]
    assert all(stage["status"] == "pending" for stage in run["stages"])

    list_sessions = async_client.get(
        f"/api/v1/projects/{project['id']}/sessions",
        headers=_auth_headers(fake_user),
    )
    assert list_sessions.status_code == 200
    [updated_session] = list_sessions.json()
    assert updated_session["current_pipeline_run_id"] == run["id"]

    get_resp = async_client.get(
        f"/api/v1/pipeline-runs/{run['id']}",
        headers=_auth_headers(fake_user),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run["id"]


def test_create_pipeline_run_respects_intent_and_stage_overrides(
    async_client: TestClient,
    fake_user: User,
):
    project = _create_project(async_client, fake_user)
    session = _create_project_session(async_client, fake_user, project["id"], "iteration")

    resp = async_client.post(
        f"/api/v1/sessions/{session['id']}/pipeline-runs",
        json={
            "intent_type": "iteration",
            "stage_overrides": {"impact": False, "frontend_dev": False},
        },
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 201
    run = resp.json()
    assert [stage["stage_id"] for stage in run["stages"]] == [
        "diff",
        "impact",
        "backend_dev",
        "frontend_dev",
        "regression",
    ]
    stage_by_id = {stage["stage_id"]: stage for stage in run["stages"]}
    assert stage_by_id["diff"]["status"] == "pending"
    assert stage_by_id["impact"]["status"] == "skipped"
    assert stage_by_id["impact"]["skip_reason"] == "user_override"
    assert stage_by_id["frontend_dev"]["status"] == "skipped"
    assert stage_by_id["frontend_dev"]["required"] is False
    assert run["current_stage_id"] == "diff"


def test_skip_and_restore_optional_stage(async_client: TestClient, fake_user: User):
    project = _create_project(async_client, fake_user)
    session = _create_project_session(async_client, fake_user, project["id"], "iteration")
    run = async_client.post(
        f"/api/v1/sessions/{session['id']}/pipeline-runs",
        json={"intent_type": "iteration"},
        headers=_auth_headers(fake_user),
    ).json()

    skip_resp = async_client.post(
        f"/api/v1/pipeline-runs/{run['id']}/stages/impact/skip",
        headers=_auth_headers(fake_user),
    )
    assert skip_resp.status_code == 200
    stage_by_id = {stage["stage_id"]: stage for stage in skip_resp.json()["stages"]}
    assert stage_by_id["impact"]["status"] == "skipped"
    assert stage_by_id["impact"]["skip_reason"] == "user_skipped"

    restore_resp = async_client.post(
        f"/api/v1/pipeline-runs/{run['id']}/stages/impact/restore",
        headers=_auth_headers(fake_user),
    )
    assert restore_resp.status_code == 200
    stage_by_id = {stage["stage_id"]: stage for stage in restore_resp.json()["stages"]}
    assert stage_by_id["impact"]["status"] == "pending"
    assert stage_by_id["impact"]["skip_reason"] is None

    required_skip_resp = async_client.post(
        f"/api/v1/pipeline-runs/{run['id']}/stages/diff/skip",
        headers=_auth_headers(fake_user),
    )
    assert required_skip_resp.status_code == 400


def test_start_and_complete_stage_advances_current_stage(
    async_client: TestClient,
    fake_user: User,
):
    project = _create_project(async_client, fake_user)
    session = _create_project_session(async_client, fake_user, project["id"], "bug_fix")
    run = async_client.post(
        f"/api/v1/sessions/{session['id']}/pipeline-runs",
        json={"intent_type": "bug_fix"},
        headers=_auth_headers(fake_user),
    ).json()

    start_resp = async_client.post(
        f"/api/v1/pipeline-runs/{run['id']}/stages/locate/start",
        headers=_auth_headers(fake_user),
    )
    assert start_resp.status_code == 200
    started = start_resp.json()
    assert started["status"] == "running"
    assert started["current_stage_id"] == "locate"
    assert started["stages"][0]["status"] == "running"

    complete_resp = async_client.post(
        f"/api/v1/pipeline-runs/{run['id']}/stages/locate/complete",
        headers=_auth_headers(fake_user),
    )
    assert complete_resp.status_code == 200
    completed = complete_resp.json()
    assert completed["status"] == "running"
    assert completed["current_stage_id"] == "impact_scope"
    stage_by_id = {stage["stage_id"]: stage for stage in completed["stages"]}
    assert stage_by_id["locate"]["status"] == "completed"
    assert stage_by_id["impact_scope"]["status"] == "pending"


def test_chat_first_message_creates_pipeline_run(
    async_client: TestClient,
    fake_user: User,
    monkeypatch,
):
    async def noop_run_task_with_skills(**_kwargs):
        return None

    monkeypatch.setattr("api.routes.sessions._run_task_with_skills", noop_run_task_with_skills)

    project = _create_project(async_client, fake_user)
    session = _create_project_session(async_client, fake_user, project["id"], "ui_adjust")

    chat_resp = async_client.post(
        f"/api/v1/sessions/{session['id']}/chat",
        json={
            "content": "把项目卡片的视觉层级调清楚",
            "intent": "ui_adjust",
        },
        headers=_auth_headers(fake_user),
    )

    assert chat_resp.status_code == 202
    chat_body = chat_resp.json()
    assert chat_body["pipeline_run_id"]

    list_sessions = async_client.get(
        f"/api/v1/projects/{project['id']}/sessions",
        headers=_auth_headers(fake_user),
    )
    assert list_sessions.status_code == 200
    [updated_session] = list_sessions.json()
    run_id = updated_session["current_pipeline_run_id"]
    assert run_id
    assert chat_body["pipeline_run_id"] == run_id

    run_resp = async_client.get(
        f"/api/v1/pipeline-runs/{run_id}",
        headers=_auth_headers(fake_user),
    )
    assert run_resp.status_code == 200
    run = run_resp.json()
    assert run["intent_type"] == "ui_adjust"
    assert [stage["stage_id"] for stage in run["stages"]] == [
        "prototype_diff",
        "frontend_dev",
        "visual",
    ]
