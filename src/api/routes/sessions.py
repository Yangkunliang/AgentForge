"""会话（Session）与对话（Chat）路由"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.api.execution_steps import ExecutionStepCollector
from agent_forge.api.sse import emit_task_started, get_sse_manager
from agent_forge.bridge.files import BridgeAccessError, read_mount_file
from agent_forge.database import get_async_session
from agent_forge.models import Artifact, AuditLog, Project, ProjectMount, Task, TaskStatus, User
from agent_forge.models.session import Message, Session
from agent_forge.models.user_agent_settings import UserAgentSettings
from agent_forge.pipeline.service import create_pipeline_run_for_session
from agent_forge.tracing import get_trace_id, get_tracer
from middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("agent_forge")


class SessionResponse(BaseModel):
    id: str
    project_id: str | None
    title: str
    intent_type: str | None = None
    current_pipeline_run_id: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class MessageArtifactResponse(BaseModel):
    id: str
    project_id: str
    session_id: str | None
    pipeline_run_id: str | None
    stage_state_id: str | None
    artifact_type: str
    name: str
    content: str
    file_type: str | None
    source_message_id: str | None
    metadata: dict
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    task_id: str | None
    extra_data: list | None = None
    artifacts: list[MessageArtifactResponse] = Field(default_factory=list)
    created_at: datetime
    model_config = {"from_attributes": True}


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class ContextFileItem(BaseModel):
    type: Literal["branch", "file", "url", "artifact"]
    value: str = Field(..., min_length=1, max_length=2000)
    label: str | None = Field(default=None, max_length=500)
    mount_id: str | None = Field(default=None, max_length=50)


class SkillAuthorizationRequest(BaseModel):
    authorized_skill_names: list[str] = Field(default_factory=list, max_length=20)
    authorized_permissions: list[str] = Field(default_factory=list, max_length=20)
    source: str = Field(default="user_confirmation", max_length=80)


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000, description="用户消息（最多 50000 字符）")
    intent: Literal["new_feature", "iteration", "ui_adjust", "bug_fix"] | None = Field(
        default=None,
        description="用户选择的需求类型",
    )
    context_files: list[ContextFileItem] = Field(
        default_factory=list,
        description="用户主动指定的上下文线索",
    )
    stage_overrides: dict[str, bool] = Field(
        default_factory=dict,
        description="执行阶段开关覆盖，false 表示用户显式跳过",
    )
    skill_authorization: SkillAuthorizationRequest | None = Field(
        default=None,
        description="当前阶段一次性 Skill 授权上下文",
    )


class ChatResponse(BaseModel):
    message_id: str
    task_id: str
    pipeline_run_id: str | None = None


def _artifact_to_dict(artifact: Artifact) -> dict:
    return {
        "id": artifact.id,
        "project_id": artifact.project_id,
        "session_id": artifact.session_id,
        "pipeline_run_id": artifact.pipeline_run_id,
        "stage_state_id": artifact.stage_state_id,
        "artifact_type": artifact.artifact_type,
        "name": artifact.name,
        "content": artifact.content,
        "file_type": artifact.file_type,
        "source_message_id": artifact.source_message_id,
        "metadata": artifact.metadata_json or {},
        "created_at": artifact.created_at,
        "updated_at": artifact.updated_at,
    }


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
    project = await _get_or_create_default_project(db, current_user.id)
    session = Session(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        project_id=project.id,
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
) -> list[dict]:
    await _get_session_or_404(db, session_id, current_user.id)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = list(result.scalars().all())
    message_ids = [message.id for message in messages]
    artifacts_by_message: dict[str, list[dict]] = defaultdict(list)

    if message_ids:
        artifact_result = await db.execute(
            select(Artifact)
            .where(Artifact.source_message_id.in_(message_ids))
            .order_by(Artifact.created_at.asc())
        )
        for artifact in artifact_result.scalars().all():
            if artifact.source_message_id:
                artifacts_by_message[artifact.source_message_id].append(_artifact_to_dict(artifact))

    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "task_id": message.task_id,
            "extra_data": message.extra_data,
            "artifacts": artifacts_by_message.get(message.id, []),
            "created_at": message.created_at,
        }
        for message in messages
    ]


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

    pipeline_run_id = session.current_pipeline_run_id
    if not pipeline_run_id:
        run = await create_pipeline_run_for_session(
            db,
            session=session,
            intent_type=body.intent,
            stage_overrides=body.stage_overrides,
        )
        pipeline_run_id = run.id

    advanced_context = await _build_advanced_context(
        body,
        db=db,
        session=session,
        user_id=current_user.id,
    )

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
            pipeline_run_id=pipeline_run_id,
            advanced_context=advanced_context,
        )
    )

    return {"message_id": user_msg.id, "task_id": task_id, "pipeline_run_id": pipeline_run_id}


async def _get_session_or_404(db: AsyncSession, session_id: str, user_id: str) -> Session:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _get_or_create_default_project(db: AsyncSession, user_id: str) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.user_id == user_id,
            Project.name == "默认项目",
            Project.status == "active",
        )
    )
    project = result.scalar_one_or_none()
    if project:
        return project

    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="默认项目",
        description="兼容旧会话入口自动创建的默认项目",
        tech_tags=[],
        status="active",
    )
    db.add(project)
    await db.flush()
    return project


async def _build_advanced_context(
    body: ChatRequest,
    *,
    db: AsyncSession,
    session: Session,
    user_id: str,
) -> dict:
    """提取高级设置上下文，供 SkillExecutionEngine 注入 system prompt。"""
    context: dict = {}
    if body.intent:
        context["intent"] = body.intent
    if body.context_files:
        context["context_files"] = [
            await _hydrate_context_file(item, db=db, session=session, user_id=user_id)
            for item in body.context_files
        ]
    if body.stage_overrides:
        context["stage_overrides"] = body.stage_overrides
    if body.skill_authorization:
        authorization = body.skill_authorization.model_dump()
        if authorization["authorized_skill_names"] or authorization["authorized_permissions"]:
            context["skill_authorization"] = authorization
    return context


async def _hydrate_context_file(
    item: ContextFileItem,
    *,
    db: AsyncSession,
    session: Session,
    user_id: str,
) -> dict:
    context_item = item.model_dump(exclude_none=True)
    if item.type != "file" or not item.mount_id:
        return context_item
    if not session.project_id:
        raise HTTPException(status_code=400, detail="File context requires a project session")

    result = await db.execute(
        select(ProjectMount)
        .join(Project, ProjectMount.project_id == Project.id)
        .where(
            ProjectMount.id == item.mount_id,
            ProjectMount.project_id == session.project_id,
            Project.user_id == user_id,
            Project.status != "archived",
        )
    )
    mount = result.scalar_one_or_none()
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")
    if mount.mount_type not in ("local", "upload"):
        raise HTTPException(status_code=400, detail="Only local or upload mounts support file context")
    if mount.status != "connected":
        raise HTTPException(status_code=409, detail="Mount is not connected")

    try:
        content = read_mount_file(mount, item.value)
    except BridgeAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if mount.mount_type == "upload":
        db.add(
            AuditLog(
                id=str(uuid.uuid4()),
                action="upload_mount.file.read",
                resource="upload_mount",
                user_id=user_id,
                trace_id=get_trace_id() or session.id,
                status="success",
                degraded=False,
                details={
                    "project_id": session.project_id,
                    "mount_id": mount.id,
                    "path": content["path"],
                    "size": content["size"],
                    "truncated": content["truncated"],
                },
            )
        )

    context_item.update(
        {
            "source": "project_mount",
            "content": content["content"],
            "content_truncated": content["truncated"],
            "size": content["size"],
        }
    )
    return context_item


async def _run_task_with_skills(
    task_id: str,
    trace_id: str,
    session_id: str,
    assistant_msg_id: str,
    user_message: str,
    history_messages: list[Message],
    user_id: str | None = None,
    agent_name: str = "CodeSoul",
    pipeline_run_id: str | None = None,
    advanced_context: dict | None = None,
) -> None:
    from agent_forge.api.sse import emit_task_completed, emit_task_failed, get_sse_manager
    from agent_forge.config import settings
    from agent_forge.database import async_session_factory
    from agent_forge.llm.provider import LLMConfig, get_llm_provider
    from agent_forge.pipeline.runtime import StageRuntime
    from agent_forge.skills.registry import get_skill_registry
    from agent_forge.tracing import get_tracer, start_task_trace

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

                runtime = StageRuntime(session_factory=async_session_factory)

                full_content = ""
                execution_step_collector = ExecutionStepCollector()

                async def sse_publish_and_collect(event_type: str, data: dict) -> None:
                    """SSE 发射同时收集 execution_steps 事件。"""
                    await sse.publish(task_id, event_type, data)
                    execution_step_collector.collect(event_type, data)

                async_gen = runtime.run_current_stage(
                    task_id=task_id,
                    pipeline_run_id=pipeline_run_id,
                    user_message=user_message,
                    conversation_history=conversation_history,
                    tools=tools,
                    llm=get_llm_provider(),
                    config=llm_config,
                    sse_publish=sse_publish_and_collect,
                    user_id=user_id,
                    agent_name=agent_name,
                    advanced_context=advanced_context,
                    source_message_id=assistant_msg_id,
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
                            if execution_step_collector.steps:
                                msg.extra_data = execution_step_collector.steps

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
