"""费用统计 API 测试。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.models.task import Task, TaskStatus
from agent_forge.models.task_execution import TaskExecution
from agent_forge.models.user import User


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


def _cost_task(
    *,
    task_id: str,
    user_id: str | None,
    created_by: str,
    cost: float,
    created_at: datetime,
) -> Task:
    return Task(
        id=task_id,
        user_id=user_id,
        created_by=created_by,
        title=task_id,
        description=f"description-{task_id}",
        status=TaskStatus.COMPLETED,
        priority=1,
        total_cost_usd=cost,
        created_at=created_at,
    )


def _task_execution(
    *,
    execution_id: str,
    task_id: str,
    model: str,
    cost: float,
) -> TaskExecution:
    return TaskExecution(
        id=execution_id,
        task_id=task_id,
        model_used=model,
        cost_usd=cost,
        status="success",
    )


@pytest.mark.asyncio
async def test_daily_cost_route_is_registered_and_user_isolated(
    async_client: TestClient,
    db: AsyncSession,
    fake_user: User,
):
    suffix = uuid.uuid4().hex[:8]
    other_user = User(
        id=f"cost-other-user-{suffix}",
        username=f"cost-other-{suffix}",
        email=f"cost-other-{suffix}@example.com",
        password_hash="not-used-in-cost-test",
        permissions=["read"],
    )
    target_time = datetime(2031, 1, 15, 9, 0, tzinfo=UTC)
    own_first = _cost_task(
        task_id=f"cost-own-first-{suffix}",
        user_id=fake_user.id,
        created_by=fake_user.id,
        cost=1.25,
        created_at=target_time,
    )
    own_second = _cost_task(
        task_id=f"cost-own-second-{suffix}",
        user_id=fake_user.id,
        created_by=fake_user.id,
        cost=0.75,
        created_at=target_time,
    )
    other_task = _cost_task(
        task_id=f"cost-other-{suffix}",
        user_id=other_user.id,
        created_by=other_user.id,
        cost=99.0,
        created_at=target_time,
    )
    unowned_task = _cost_task(
        task_id=f"cost-unowned-{suffix}",
        user_id=None,
        created_by=fake_user.id,
        cost=77.0,
        created_at=target_time,
    )
    db.add_all(
        [
            other_user,
            own_first,
            own_second,
            other_task,
            unowned_task,
            _task_execution(
                execution_id=f"cost-exec-own-first-{suffix}",
                task_id=own_first.id,
                model="owner-model",
                cost=0.4,
            ),
            _task_execution(
                execution_id=f"cost-exec-own-second-{suffix}",
                task_id=own_second.id,
                model="owner-model",
                cost=0.6,
            ),
            _task_execution(
                execution_id=f"cost-exec-other-{suffix}",
                task_id=other_task.id,
                model="foreign-model",
                cost=55.0,
            ),
            _task_execution(
                execution_id=f"cost-exec-unowned-{suffix}",
                task_id=unowned_task.id,
                model="unowned-model",
                cost=44.0,
            ),
        ]
    )
    await db.commit()

    response = async_client.get(
        "/api/v1/cost",
        params={"date": "2031-01-15"},
        headers=_auth_headers(fake_user),
    )

    assert response.status_code == 200
    assert response.json() == {
        "date": "2031-01-15",
        "total_cost_usd": 2.0,
        "model_costs": {"owner-model": 1.0},
        "total_tasks": 2,
        "avg_cost_per_task": 1.0,
    }
