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
from agent_forge.models.user_agent_settings import UserAgentSettings
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
    extra_data: list | None = None
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
        # 标题生成延迟到任务完成后，由异步任务用 LLM 生成并通过 SSE 推送给前端
        # 保持默认占位，避免中间状态显示截断前缀
        session.title = "新对话"

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

    # 查询用户自定义的 AI 助手名称，传给异步任务
    agent_name = "CodeSoul"
    try:
        sa = await db.execute(
            select(UserAgentSettings).where(UserAgentSettings.user_id == current_user.id)
        )
        settings = sa.scalar_one_or_none()
        if settings:
            agent_name = settings.agent_name or "CodeSoul"
    except Exception:
        pass

    asyncio.create_task(
        _run_task_with_skills(
            task_id=task_id,
            trace_id=trace_id,
            session_id=session_id,
            assistant_msg_id=assistant_msg.id,
            user_message=body.content,
            history_messages=history_messages,
            user_id=current_user.id,
            agent_name=agent_name,
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
    session_id: str,
    assistant_msg_id: str,
    user_message: str,
    history_messages: list[Message],
    user_id: str | None = None,
    agent_name: str = "CodeSoul",
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
                execution_steps: list[dict] = []  # 收集执行过程数据用于持久化

                async def sse_publish_and_collect(event_type: str, data: dict) -> None:
                    """SSE 发射同时收集 execution_steps 事件。"""
                    await sse.publish(task_id, event_type, data)
                    # 收集需要持久化的步骤事件
                    if event_type == "thinking_start":
                        execution_steps.append({"type": "thinking", "content": "", "streaming": False})
                    elif event_type == "thinking_delta":
                        if execution_steps and execution_steps[-1]["type"] == "thinking":
                            execution_steps[-1]["content"] += data.get("delta", "")
                    elif event_type == "thinking_end":
                        if execution_steps and execution_steps[-1]["type"] == "thinking":
                            execution_steps[-1]["duration_ms"] = data.get("duration_ms", 0)
                    elif event_type == "tool_call_start":
                        execution_steps.append({
                            "type": "tool_call",
                            "tool_name": data.get("tool_name", ""),
                            "arguments": data.get("arguments", {}),
                            "status": "running",
                        })
                    elif event_type == "tool_call_end":
                        for s in reversed(execution_steps):
                            if s["type"] == "tool_call" and s["tool_name"] == data.get("tool_name") and s["status"] == "running":
                                s["status"] = "completed"
                                s["result"] = data.get("result", {})
                                break
                    elif event_type == "sandbox_executing":
                        execution_steps.append({
                            "type": "code_execution",
                            "code": data.get("code", ""),
                            "status": "running",
                            "stdout": "", "stderr": "",
                        })
                    elif event_type == "sandbox_completed":
                        for s in reversed(execution_steps):
                            if s["type"] == "code_execution" and s["status"] == "running":
                                s["status"] = "completed"
                                s["exit_code"] = data.get("exit_code", 0)
                                s["duration_ms"] = data.get("duration_ms", 0)
                                break
                    elif event_type == "sandbox_timeout":
                        for s in reversed(execution_steps):
                            if s["type"] == "code_execution" and s["status"] == "running":
                                s["status"] = "timeout"
                                break
                async_gen = await engine.run(
                    user_message=user_message,
                    conversation_history=conversation_history,
                    tools=tools,
                    llm=get_llm_provider(),
                    config=llm_config,
                    sse_publish=sse_publish_and_collect,
                    user_id=user_id,
                    agent_name=agent_name,
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
                            if execution_steps:
                                msg.extra_data = execution_steps

                        await db.commit()

                await emit_task_completed(task_id, {"content": full_content})

                # ── 异步生成优质标题，推送给前端实时刷新 ────────────────
                asyncio.create_task(
                    _generate_session_title(
                        session_id=session_id,
                        user_message=user_message,
                        assistant_reply=full_content[:500],
                        task_id=task_id,
                        trace_id=trace_id,
                    )
                )

            except Exception as exc:
                logger.exception("Task %s failed: %s", task_id[:8], exc)
                async with async_session_factory() as db:
                    task_result = await db.execute(select(Task).where(Task.id == task_id))
                    task = task_result.scalar_one_or_none()
                    if task:
                        task.status = TaskStatus.FAILED
                        await db.commit()
                await emit_task_failed(task_id, str(exc))


async def _generate_session_title(
    session_id: str,
    user_message: str,
    assistant_reply: str,
    task_id: str,
    trace_id: str,
) -> None:
    """任务完成后异步生成优质会话标题，通过 SSE 实时推送前端更新。

    规则：
    - 用轻量 LLM 生成 6～12 字的中文标题，概括这次对话的主题
    - 生成失败时倒退到截取用户输入前 15 字
    - 通过 SSE session_title_updated 事件通知前端
    """
    from agent_forge.config import settings
    from agent_forge.database import async_session_factory
    from agent_forge.llm.provider import LLMConfig, get_llm_provider
    from agent_forge.tracing import start_task_trace

    try:
        llm = get_llm_provider()
        config = LLMConfig(
            model=settings.default_model or "openai/deepseek-v3",
            temperature=0.3,
            max_tokens=32,
        )
        prompt = (
            f"用户说：{user_message[:200]}\n\n"
            f"AI 回复：{assistant_reply[:300]}\n\n"
            "请用 6～12 个中文字为这次对话起一个简洁标题，"
            "只输出标题文字，不加引号、标点、序号，不加任何其他内容。"
        )
        response = await llm.complete(prompt, config)
        title = response.content.strip().strip('"\'《》【】').strip()[:20]
        if not title:
            raise ValueError("empty title")
    except Exception as e:
        logger.warning("_generate_session_title: LLM 失败，使用截断占位: %s", e)
        title = user_message.strip()[:15]

    # 写入数据库
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Session).where(Session.id == session_id))
            session = result.scalar_one_or_none()
            if session:
                session.title = title
                await db.commit()
    except Exception as e:
        logger.warning("_generate_session_title: DB 写入失败: %s", e)
        return

    # 通过 SSE 推送标题更新事件，前端监听后刷新侧边栏
    try:
        sse = get_sse_manager()
        await sse.publish(task_id, "session_title_updated", {
            "session_id": session_id,
            "title": title,
        })
        logger.info("session_title_updated session_id=%s title=%r", session_id[:8], title)
    except Exception as e:
        logger.warning("_generate_session_title: SSE 推送失败: %s", e)
