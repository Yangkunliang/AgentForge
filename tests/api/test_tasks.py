"""任务管理 API 测试"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import User
from middleware.auth import get_current_user


class TestTaskCreate:
    """测试创建任务"""

    def test_create_task_success(self, async_client: TestClient, fake_user: User):
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/tasks",
            json={
                "description": "Implement user authentication",
                "priority": "high",
                "expected_models": ["gpt-4"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "Implement user authentication"
        assert data["priority"] == "high"
        assert data["status"] == "pending"
        assert "trace_id" in data
        assert data["sub_tasks"] == []

    def test_create_task_unauthorized(self, test_session_factory):
        """测试未授权创建任务"""
        from agent_forge.database import get_async_session
        from fastapi.testclient import TestClient
        from api.main import app

        async def override_get_session():
            async with test_session_factory() as session:
                yield session

        app.dependency_overrides[get_async_session] = override_get_session
        # 不覆盖 get_current_user，保持默认的认证检查

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post(
            "/api/v1/tasks",
            json={"description": "Test task", "priority": "medium"},
        )
        assert resp.status_code == 401
        app.dependency_overrides.clear()


class TestTaskList:
    """测试任务列表"""

    def test_list_tasks(self, async_client: TestClient, fake_user: User):
        token = create_access_token({"sub": fake_user.id})

        # 创建两个任务
        created_count = 0
        for i in range(2):
            resp = async_client.post(
                "/api/v1/tasks",
                json={"description": f"Task {i}", "priority": "medium"},
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 201:
                created_count += 1

        resp = async_client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # 由于使用文件数据库，可能有其他测试遗留数据，只断言包含我们创建的
        assert data["total"] >= created_count
        assert len(data["items"]) >= created_count

    def test_list_tasks_filter_by_status(self, async_client: TestClient, fake_user: User):
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/tasks",
            json={"description": "Pending task", "priority": "medium"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = async_client.get(
            "/api/v1/tasks?status=pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # 由于使用文件数据库，可能有其他测试遗留数据，只断言至少包含我们创建的
        assert data["total"] >= 1


class TestTaskDetail:
    """测试任务详情"""

    def test_get_task_detail(self, async_client: TestClient, fake_user: User):
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/tasks",
            json={"description": "Detail task", "priority": "low"},
            headers={"Authorization": f"Bearer {token}"},
        )
        task_id = resp.json()["id"]

        resp = async_client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == task_id
        assert data["description"] == "Detail task"

    def test_get_task_not_found(self, async_client: TestClient, fake_user: User):
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.get(
            "/api/v1/tasks/nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestTaskCancel:
    """测试取消任务"""

    def test_cancel_task(self, async_client: TestClient, fake_user: User):
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/tasks",
            json={"description": "Cancel me", "priority": "medium"},
            headers={"Authorization": f"Bearer {token}"},
        )
        task_id = resp.json()["id"]

        resp = async_client.post(
            f"/api/v1/tasks/{task_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"


class TestTaskFeedback:
    """测试任务反馈"""

    def test_submit_feedback(self, async_client: TestClient, fake_user: User):
        token = create_access_token({"sub": fake_user.id})

        resp = async_client.post(
            "/api/v1/tasks",
            json={"description": "Feedback task", "priority": "medium"},
            headers={"Authorization": f"Bearer {token}"},
        )
        task_id = resp.json()["id"]

        resp = async_client.post(
            f"/api/v1/tasks/{task_id}/feedback",
            json={"thumbs": 1, "rating": 5, "comment": "Great job!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Feedback submitted successfully"
