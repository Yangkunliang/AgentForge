"""会话（Session）与对话（Chat）路由

面向终端用户，多 Agent 执行细节对用户透明。
用户视角只有「会话」和「消息」。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_forge.api.sse import get_sse_manager, emit_task_started
from agent_forge.database import get_async_session
from agent_forge.models import Task, TaskPriority, TaskStatus, User
from agent_forge.models.session import Session, Message
from middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("agent_forge")


# ── Pydantic schemas ──────────────────────────────────────────


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    task_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RenameSessionRequest(BaseModel):
    title: str


class ChatRequest(BaseModel):
    content: str


class ChatResponse(BaseModel):
    message_id: str
    task_id: str


# ── 会话管理 ──────────────────────────────────────────────────


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[Session]:
    """获取当前用户的会话列表（按最近更新倒序）"""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.updated_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Session:
    """新建一个对话会话"""
    session = Session(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        title="新对话",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: str,
    body: RenameSessionRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Session:
    """重命名会话标题"""
    session = await _get_session_or_404(db, session_id, current_user.id)
    session.title = body.title.strip()[:100]
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """删除会话（级联删除所有消息）"""
    session = await _get_session_or_404(db, session_id, current_user.id)
    await db.delete(session)
    await db.commit()


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[Message]:
    """获取会话的历史消息"""
    await _get_session_or_404(db, session_id, current_user.id)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


# ── 对话发送 ──────────────────────────────────────────────────


@router.post("/{session_id}/chat", response_model=ChatResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    session_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    发送用户消息，异步触发多 Agent 执行。

    返回 task_id 供前端订阅 SSE 流：
      GET /api/v1/sse/tasks/{task_id}/stream
    """
    session = await _get_session_or_404(db, session_id, current_user.id)

    # 1. 若为首条消息，用内容前 20 字作为会话标题
    if session.title == "新对话":
        session.title = body.content.strip()[:20]

    # 2. 生成 task_id，先写 Task（Message 外键依赖它）
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        user_id=current_user.id,
        created_by=current_user.id,
        title=body.content.strip()[:100],
        description=body.content,
        priority=1,  # MEDIUM
        trace_id=str(uuid.uuid4()),
        status=TaskStatus.PENDING,
    )
    db.add(task)

    # 3. 写入用户消息（task_id=None，用户消息本身不绑定 Task）
    user_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=body.content,
        task_id=None,
    )
    db.add(user_msg)

    # 4. 预创建 assistant 占位消息（content 为空，SSE 完成后更新）
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content="",
        task_id=task_id,
    )
    db.add(assistant_msg)

    # 更新 session.updated_at 使其排在列表最前
    session.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # 5. 异步启动执行（不阻塞响应），执行完成后更新 assistant 消息
    asyncio.create_task(
        _run_task_and_update_message(task_id, assistant_msg.id, body.content)
    )

    return {"message_id": user_msg.id, "task_id": task_id}


# ── 内部辅助 ─────────────────────────────────────────────────


async def _get_session_or_404(db: AsyncSession, session_id: str, user_id: str) -> Session:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _run_task_and_update_message(task_id: str, assistant_msg_id: str, description: str) -> None:
    """
    后台执行任务，完成后将结果写回 assistant 消息。
    多 Agent 的协作细节（Contract Net、子任务分配）在 executor 内完成，
    这里只关心最终结果。
    """
    from agent_forge.database import async_session_factory
    from agent_forge.api.sse import emit_task_completed, emit_task_failed, get_sse_manager

    sse = get_sse_manager()

    try:
        # 推送开始事件
        await emit_task_started(task_id, task_id)

        # TODO: 接入真实 executor
        # result = await executor.execute_task(task)
        # 目前 mock 一个响应，待 TASK-003 executor 完成后替换
        await asyncio.sleep(0.5)
        result_content = f"已收到您的请求：「{description}」\n\n（多 Agent 正在处理中，executor 接入后将返回真实结果）"

        # 更新数据库
        async with async_session_factory() as db:
            # 更新 Task 状态
            task_result = await db.execute(select(Task).where(Task.id == task_id))
            task = task_result.scalar_one_or_none()
            if task:
                task.status = TaskStatus.COMPLETED
                task.result = result_content
                task.completed_at = datetime.now(timezone.utc)

            # 更新 assistant 消息内容
            msg_result = await db.execute(select(Message).where(Message.id == assistant_msg_id))
            msg = msg_result.scalar_one_or_none()
            if msg:
                msg.content = result_content

            await db.commit()

        # 推送完成事件（前端 useSSE 监听此事件更新气泡）
        await emit_task_completed(task_id, {"content": result_content})

    except Exception as exc:
        logger.exception(f"Task {task_id} failed: {exc}")

        async with async_session_factory() as db:
            task_result = await db.execute(select(Task).where(Task.id == task_id))
            task = task_result.scalar_one_or_none()
            if task:
                task.status = TaskStatus.FAILED
                await db.commit()

        from agent_forge.api.sse import emit_task_failed
        await emit_task_failed(task_id, str(exc))
