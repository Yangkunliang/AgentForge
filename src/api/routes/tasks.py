"""任务管理路由"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_forge.database import get_async_session
from agent_forge.models import Task, TaskPriority, TaskStatus, User
from api.schemas.task import (
    TaskCreateRequest,
    TaskDetailResponse,
    TaskFeedbackRequest,
    TaskFeedbackResponse,
    TaskListResponse,
)
from middleware.auth import get_current_user, require_permission

router = APIRouter()
logger = logging.getLogger("agent_forge")


_INT_TO_PRIORITY = {0: TaskPriority.LOW, 1: TaskPriority.MEDIUM, 2: TaskPriority.HIGH}


def _resolve_priority(value: int | str | TaskPriority) -> str:
    """将整数或字符串统一转成 TaskPriority value 字符串"""
    if isinstance(value, TaskPriority):
        return value.value
    if isinstance(value, int):
        return _INT_TO_PRIORITY.get(value, TaskPriority.MEDIUM).value
    # 已经是字符串时直接走枚举校验
    return TaskPriority(value).value


def _task_to_dict(task: Task) -> dict:
    """将 Task 模型转为字典（避免 Pydantic from_attributes 的 async 问题）"""
    from sqlalchemy import inspect as sa_inspect

    # 检查 sub_tasks 是否已加载，避免触发懒加载
    sub_tasks = []
    if "sub_tasks" not in sa_inspect(task).unloaded:
        sub_tasks = [
            {
                "id": st.id,
                "description": st.description,
                "status": st.status.value if hasattr(st.status, "value") else st.status,
                "assigned_agent_id": st.assigned_agent_id,
                "result": st.result,
            }
            for st in task.sub_tasks
        ]

    return {
        "id": task.id,
        "description": task.description,
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "priority": _resolve_priority(task.priority),
        "result": task.result,
        "trace_id": task.trace_id,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
        "sub_tasks": sub_tasks,
    }


@router.post("", response_model=TaskDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """创建任务"""
    trace_id = str(uuid.uuid4())
    task = Task(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        created_by=current_user.id,
        title=body.description[:255],
        description=body.description,
        priority={"low": 0, "medium": 1, "high": 2}[body.priority],
        trace_id=trace_id,
        status=TaskStatus.PENDING,
        result=None,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _task_to_dict(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
) -> dict:
    """获取任务列表（支持分页和过滤）"""
    query = select(Task).where(Task.user_id == current_user.id)
    count_query = select(func.count(Task.id)).where(Task.user_id == current_user.id)

    if status_filter:
        query = query.where(Task.status == TaskStatus(status_filter))
        count_query = count_query.where(Task.status == TaskStatus(status_filter))
    if priority:
        priority_int = {
            "low": 0, "medium": 1, "high": 2,
        }.get(priority.lower(), 1)
        query = query.where(Task.priority == priority_int)
        count_query = count_query.where(Task.priority == priority_int)

    # 分页
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    tasks = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": t.id,
                "description": t.description,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "priority": _resolve_priority(t.priority),
                "trace_id": t.trace_id,
                "created_at": t.created_at,
                "completed_at": t.completed_at,
            }
            for t in tasks
        ],
    }


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取任务详情"""
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.sub_tasks))
        .where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_dict(task)


@router.post("/{task_id}/cancel", response_model=TaskDetailResponse)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """取消任务"""
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.sub_tasks))
        .where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in (TaskStatus.PENDING, TaskStatus.PROCESSING):
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    task.status = TaskStatus.CANCELLED
    await db.commit()
    await db.refresh(task)
    return _task_to_dict(task)


@router.post("/{task_id}/feedback", response_model=TaskFeedbackResponse)
async def submit_feedback(
    task_id: str,
    body: TaskFeedbackRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """提交任务反馈"""
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 将反馈存入 task 的 result 或额外字段
    # 目前简单存储在 result 中（JSON 格式）
    feedback = {
        "thumbs": body.thumbs,
        "rating": body.rating,
        "comment": body.comment,
    }
    task.result = str(feedback) if task.result is None else f"{task.result} | feedback: {feedback}"

    await db.commit()
    return {"message": "Feedback submitted successfully"}
