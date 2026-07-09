"""Agent 管理 API 测试"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import User
from middleware.auth import get_current_user


class TestAgentCreate:
    """测试创建 Agent"""

    def test_create_agent_admin(self, async_client: TestClient, fake_user: User):
        # 给 fake_user 添加 admin 权限
        fake_user.permissions = ["admin"]
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/agents",
            json={
                "name": "designer-agent",
                "capabilities": ["ui_design", "code_review"],
                "model": "gpt-4",
                "description": "A designer agent",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "designer-agent"
        assert data["status"] == "active"

    def test_create_agent_duplicate_name(self, async_client: TestClient, fake_user: User):
        fake_user.permissions = ["admin"]
        token = create_access_token({"sub": fake_user.id})

        # 第一次创建
        async_client.post(
            "/api/v1/agents",
            json={"name": "dup-agent", "capabilities": [], "model": "gpt-4"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # 重复创建
        resp = async_client.post(
            "/api/v1/agents",
            json={"name": "dup-agent", "capabilities": [], "model": "gpt-4"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    def test_create_agent_forbidden(self, async_client: TestClient, fake_user: User):
        # 普通用户（无 admin 权限）
        fake_user.permissions = ["read"]
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/agents",
            json={"name": "test-agent", "capabilities": [], "model": "gpt-4"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestAgentList:
    """测试 Agent 列表"""

    def test_list_agents(self, async_client: TestClient, fake_user: User):
        fake_user.permissions = ["admin"]
        token = create_access_token({"sub": fake_user.id})

        # 创建两个 Agent
        created_names = set()
        for name in ["agent-1", "agent-2"]:
            async_client.post(
                "/api/v1/agents",
                json={"name": name, "capabilities": ["code"], "model": "gpt-4"},
                headers={"Authorization": f"Bearer {token}"},
            )
            created_names.add(name)

        resp = async_client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # 由于使用文件数据库，可能有其他测试遗留数据，只断言包含我们创建的
        assert len(data) >= 2
        returned_names = {a["name"] for a in data}
        assert created_names.issubset(returned_names)


class TestAgentRuntimeCandidates:
    """测试运行时 Agent 候选接口"""

    def test_runtime_candidates_only_return_active_agents(
        self,
        async_client: TestClient,
        fake_user: User,
    ):
        fake_user.permissions = ["admin"]
        token = create_access_token({"sub": fake_user.id})

        active_name = f"runtime-coder-{uuid.uuid4()}"
        inactive_name = f"runtime-inactive-{uuid.uuid4()}"
        active = async_client.post(
            "/api/v1/agents",
            json={"name": active_name, "capabilities": ["code_generation"], "model": "gpt-4"},
            headers={"Authorization": f"Bearer {token}"},
        )
        inactive = async_client.post(
            "/api/v1/agents",
            json={"name": inactive_name, "capabilities": ["code_generation"], "model": "gpt-4"},
            headers={"Authorization": f"Bearer {token}"},
        )
        async_client.patch(
            f"/api/v1/agents/{inactive.json()['id']}",
            json={"status": "inactive"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = async_client.get(
            "/api/v1/agents/runtime/candidates?stage_selector=coder",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        names = {agent["name"] for agent in data["items"]}
        assert active.json()["name"] in names
        assert inactive.json()["name"] not in names
        active_item = next(agent for agent in data["items"] if agent["id"] == active.json()["id"])
        assert active_item["recommended"] is True


class TestAgentUpdate:
    """测试更新 Agent"""

    def test_update_agent(self, async_client: TestClient, fake_user: User):
        fake_user.permissions = ["admin"]
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/agents",
            json={"name": "update-agent", "capabilities": [], "model": "gpt-4"},
            headers={"Authorization": f"Bearer {token}"},
        )
        agent_id = resp.json()["id"]

        resp = async_client.patch(
            f"/api/v1/agents/{agent_id}",
            json={"status": "inactive", "description": "Updated description"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "inactive"
        assert data["description"] == "Updated description"


class TestAgentDelete:
    """测试删除 Agent"""

    def test_delete_agent(self, async_client: TestClient, fake_user: User):
        fake_user.permissions = ["admin"]
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/agents",
            json={"name": "delete-agent", "capabilities": [], "model": "gpt-4"},
            headers={"Authorization": f"Bearer {token}"},
        )
        agent_id = resp.json()["id"]

        resp = async_client.delete(
            f"/api/v1/agents/{agent_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        # 确认已删除
        resp = async_client.get(
            f"/api/v1/agents/{agent_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
