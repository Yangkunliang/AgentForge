"""会话（Session）与对话（Chat）路由"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.api.sse import get_sse_manager, emit_task_started
from agent_forge.database import get_async_session
from agent_forge.models import Task, TaskStatus, User
from agent_forge.models.session import Session, Message
from agent_forge.tracing import get_trace_id, get_tracer
from middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("agent_forge")


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
    title: str = Field(..., min_length=1, max_length=100)


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000, description="用户消息（最多 50000 字符）")


class ChatResponse(BaseModel):
    message_id: str
    task_id: str


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[Session]:
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
    session = Session(id=str(uuid.uuid4()), user_id=current_user.id, title="新对话")
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
    session = await _get_session_or_404(db, session_id, current_user.id)
    await db.delete(session)
    await db.commit()


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[Message]:
    await _get_session_or_404(db, session_id, current_user.id)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/{session_id}/chat", response_model=ChatResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    session_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    tracer = get_tracer()

    async with tracer.start_span("chat.get_session"):
        session = await _get_session_or_404(db, session_id, current_user.id)

    if session.title == "新对话":
        session.title = body.content.strip()[:20]

    task_id = str(uuid.uuid4())
    trace_id = get_trace_id() or task_id

    task = Task(
        id=task_id,
        user_id=current_user.id,
        created_by=current_user.id,
        title=body.content.strip()[:100],
        description=body.content,
        priority=1,
        trace_id=trace_id,
        status=TaskStatus.PENDING,
    )
    db.add(task)

    user_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=body.content,
        task_id=None,
    )
    db.add(user_msg)

    assistant_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content="",
        task_id=task_id,
    )
    db.add(assistant_msg)

    session.updated_at = datetime.now(timezone.utc)

    async with tracer.start_span("chat.db_commit"):
        await db.commit()

    async with tracer.start_span("chat.load_history"):
        history_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .where(Message.id != assistant_msg.id)
            .order_by(Message.created_at.asc())
        )
        history_messages = list(history_result.scalars().all())

    asyncio.create_task(
        _run_task_with_skills(
            task_id=task_id,
            trace_id=trace_id,
            assistant_msg_id=assistant_msg.id,
            user_message=body.content,
            history_messages=history_messages,
            user_id=current_user.id,
        )
    )

    return {"message_id": user_msg.id, "task_id": task_id}


async def _get_session_or_404(db: AsyncSession, session_id: str, user_id: str) -> Session:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _run_task_with_skills(
    task_id: str,
    trace_id: str,
    assistant_msg_id: str,
    user_message: str,
    history_messages: list[Message],
    user_id: str | None = None,
) -> None:
    from agent_forge.config import settings
    from agent_forge.database import async_session_factory
    from agent_forge.api.sse import emit_task_completed, emit_task_failed, get_sse_manager
    from agent_forge.llm.provider import LLMConfig, get_llm_provider
    from agent_forge.skills.dispatcher import SkillDispatcher
    from agent_forge.skills.engine import SkillExecutionEngine
    from agent_forge.skills.registry import get_skill_registry
    from agent_forge.tracing import start_task_trace, get_tracer

    sse = get_sse_manager()

    async def sse_publish(event_type: str, data: dict) -> None:
        await sse.publish(task_id, event_type, data)

    with start_task_trace(trace_id=trace_id):
        async with get_tracer().start_span(
            "task.run",
            tags={"task_id": task_id[:8], "user_msg_len": len(user_message)},
        ):
            try:
                await emit_task_started(task_id, trace_id)

                llm_config = LLMConfig(
                    model=settings.default_model or "openai/deepseek-v3",
                    temperature=settings.default_temperature,
                    max_tokens=settings.max_tokens,
                )

                async with get_tracer().start_span("task.load_skills") as sp:
                    registry = get_skill_registry()
                    tools = registry.get_all_tool_defs()
                    sp.tags["tools"] = len(tools)

                conversation_history: list[dict] = []
                for msg in history_messages[-20:]:
                    if msg.role in ("user", "assistant") and msg.content:
                        conversation_history.append({"role": msg.role, "content": msg.content})

                dispatcher = SkillDispatcher()
                engine = SkillExecutionEngine(dispatcher)

                full_content = ""
                async_gen = await engine.run(
                    user_message=user_message,
                    conversation_history=conversation_history,
                    tools=tools,
                    llm=get_llm_provider(),
                    config=llm_config,
                    sse_publish=sse_publish,
                    user_id=user_id,
                )

                async for chunk in async_gen:
                    if chunk:
                        full_content += chunk
                        await sse.publish(task_id, "llm_response", {"delta": chunk})

                if not full_content:
                    full_content = "抱歉，未能生成回复，请重试。"

                async with get_tracer().start_span("task.db_write"):
                    async with async_session_factory() as db:
                        task_result = await db.execute(select(Task).where(Task.id == task_id))
                        task = task_result.scalar_one_or_none()
                        if task:
                            task.status = TaskStatus.COMPLETED
                            task.result = full_content
                            task.completed_at = datetime.now(timezone.utc)

                        msg_result = await db.execute(
                            select(Message).where(Message.id == assistant_msg_id))
                        msg = msg_result.scalar_one_or_none()
                        if msg:
                            msg.content = full_content

                        await db.commit()

                await emit_task_completed(task_id, {"content": full_content})

            except Exception as exc:
                logger.exception("Task %s failed: %s", task_id[:8], exc)
                async with async_session_factory() as db:
                    task_result = await db.execute(select(Task).where(Task.id == task_id))
                    task = task_result.scalar_one_or_none()
                    if task:
                        task.status = TaskStatus.FAILED
                        await db.commit()
                await emit_task_failed(task_id, str(exc))
