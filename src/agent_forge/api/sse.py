"""SSE 流式输出 API"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("agent_forge.api.sse")

sse_router = APIRouter(prefix="/sse", tags=["sse"])

# 标记 SSE 流结束的哨兵值
_STREAM_DONE = "__STREAM_DONE__"


class SSEEventTypes:
    """SSE 事件类型

    分类说明：
      用户感知事件  — 在 UI 上渲染可视组件
      状态辅助事件  — 更新已有组件状态，不新增组件
      内部事件      — 前端静默忽略，不透出给用户
    """

    # ── 任务生命周期（状态辅助）────────────────────────────────
    TASK_STARTED   = "task_started"
    TASK_PROGRESS  = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED    = "task_failed"

    # ── 子任务 / 竞标（内部）──────────────────────────────────
    SUB_TASK_CREATED   = "sub_task_created"
    SUB_TASK_COMPLETED = "sub_task_completed"
    BID_RECEIVED       = "bid_received"
    AGENT_ASSIGNED     = "agent_assigned"

    # ── Skill 调用（内部，由 tool_call_* 覆盖）────────────────
    SKILL_CALLED = "skill_called"
    SKILL_RESULT = "skill_result"

    # ── LLM 输出（用户感知）───────────────────────────────────
    LLM_RESPONSE = "llm_response"

    # ── Thinking 过程（用户感知）──────────────────────────────
    THINKING_START = "thinking_start"
    THINKING_DELTA = "thinking_delta"
    THINKING_END   = "thinking_end"

    # ── 工具调用（用户感知）───────────────────────────────────
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END   = "tool_call_end"

    # ── 沙箱代码执行（用户感知）──────────────────────────────
    SANDBOX_EXECUTING = "sandbox_executing"
    SANDBOX_COMPLETED = "sandbox_completed"
    SANDBOX_TIMEOUT   = "sandbox_timeout"

    # ── Pipeline 阶段状态（状态辅助）───────────────────────────
    PIPELINE_STARTED = "pipeline_started"
    STAGE_STARTED    = "stage_started"
    STAGE_COMPLETED  = "stage_completed"
    STAGE_SKIPPED    = "stage_skipped"
    ARTIFACT_CREATED = "artifact_created"
    CONFIRM_REQUIRED = "confirm_required"
    CONFIRM_RESOLVED = "confirm_resolved"

    # ── 沙箱生命周期（内部，不透出给用户）────────────────────
    SANDBOX_CREATED   = "sandbox_created"
    SANDBOX_CONNECTED = "sandbox_connected"
    SANDBOX_PAUSED    = "sandbox_paused"
    SANDBOX_DESTROYED = "sandbox_destroyed"

    # ── 系统（内部）──────────────────────────────────────────
    ERROR     = "error"
    HEARTBEAT = "heartbeat"


class SSEManager:
    """SSE 管理器"""

    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def subscribe(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._locks:
            self._locks[task_id] = asyncio.Lock()

        queue: asyncio.Queue = asyncio.Queue()
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(queue)
        logger.debug("New subscriber for task %s", task_id)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
                logger.debug("Removed subscriber for task %s", task_id)
            except ValueError:
                pass
            # 无订阅者时清理 key
            if not self._subscribers[task_id]:
                del self._subscribers[task_id]
                self._locks.pop(task_id, None)

    async def publish(self, task_id: str, event_type: str, data: dict) -> None:
        """发布事件到所有订阅者。

        task_completed / task_failed 后额外推送哨兵，通知 stream_events 退出。
        """
        if task_id not in self._subscribers:
            return

        event = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        for queue in list(self._subscribers[task_id]):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Queue full for task %s, dropping event", task_id)

        # task_completed / task_failed 是终态事件，推完后通知关闭
        if event_type in (SSEEventTypes.TASK_COMPLETED, SSEEventTypes.TASK_FAILED):
            for queue in list(self._subscribers.get(task_id, [])):
                try:
                    queue.put_nowait(_STREAM_DONE)
                except asyncio.QueueFull:
                    pass

    async def stream_events(self, task_id: str) -> AsyncGenerator[str, None]:
        """流式事件生成器。

        收到哨兵 _STREAM_DONE 时退出，连接自然关闭。
        """
        queue = self.subscribe(task_id)

        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=30)
                except TimeoutError:
                    # 30s 无事件，发心跳保活
                    yield f"event: {SSEEventTypes.HEARTBEAT}\ndata: {{}}\n\n"
                    continue

                # 收到哨兵，退出循环，连接关闭
                if item is _STREAM_DONE or item == _STREAM_DONE:
                    logger.debug("SSE stream done for task %s", task_id)
                    return

                yield item
        except GeneratorExit:
            pass
        finally:
            self.unsubscribe(task_id, queue)


# 全局 SSE 管理器
_global_sse_manager: SSEManager | None = None


def get_sse_manager() -> SSEManager:
    global _global_sse_manager
    if _global_sse_manager is None:
        _global_sse_manager = SSEManager()
    return _global_sse_manager


@sse_router.get("/tasks/{task_id}/stream")
async def stream_task_events(task_id: str):
    return StreamingResponse(
        get_sse_manager().stream_events(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@sse_router.post("/tasks/{task_id}/events")
async def publish_task_event(task_id: str, request: Request):
    body = await request.json()
    event_type = body.get("event_type", SSEEventTypes.TASK_PROGRESS)
    data = body.get("data", {})
    await get_sse_manager().publish(task_id, event_type, data)
    return {"status": "ok"}


# ── 任务生命周期事件 ──────────────────────────────────────────

async def emit_task_started(task_id: str, trace_id: str) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.TASK_STARTED,
        {"task_id": task_id, "trace_id": trace_id},
    )


async def emit_task_completed(task_id: str, result: dict) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.TASK_COMPLETED,
        {"task_id": task_id, "content": result.get("content", "")},
    )


async def emit_task_failed(task_id: str, error: str) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.TASK_FAILED,
        {"task_id": task_id, "error": error},
    )


async def emit_pipeline_started(
    task_id: str,
    project_id: str,
    session_id: str,
    pipeline_run_id: str,
    intent_type: str,
) -> None:
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.PIPELINE_STARTED,
        {
            "task_id": task_id,
            "project_id": project_id,
            "session_id": session_id,
            "pipeline_run_id": pipeline_run_id,
            "intent_type": intent_type,
        },
    )


async def emit_stage_started(
    task_id: str,
    project_id: str,
    session_id: str,
    pipeline_run_id: str,
    stage_id: str,
) -> None:
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.STAGE_STARTED,
        {
            "task_id": task_id,
            "project_id": project_id,
            "session_id": session_id,
            "pipeline_run_id": pipeline_run_id,
            "stage_id": stage_id,
        },
    )


async def emit_stage_completed(
    task_id: str,
    project_id: str,
    session_id: str,
    pipeline_run_id: str,
    stage_id: str,
) -> None:
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.STAGE_COMPLETED,
        {
            "task_id": task_id,
            "project_id": project_id,
            "session_id": session_id,
            "pipeline_run_id": pipeline_run_id,
            "stage_id": stage_id,
        },
    )


async def emit_stage_skipped(
    task_id: str,
    project_id: str,
    session_id: str,
    pipeline_run_id: str,
    stage_id: str,
    reason: str,
) -> None:
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.STAGE_SKIPPED,
        {
            "task_id": task_id,
            "project_id": project_id,
            "session_id": session_id,
            "pipeline_run_id": pipeline_run_id,
            "stage_id": stage_id,
            "reason": reason,
        },
    )


async def emit_artifact_created(
    task_id: str,
    *,
    project_id: str,
    session_id: str | None,
    pipeline_run_id: str | None,
    stage_id: str | None,
    artifact_id: str,
    artifact_type: str,
    name: str,
) -> None:
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.ARTIFACT_CREATED,
        {
            "task_id": task_id,
            "project_id": project_id,
            "session_id": session_id,
            "pipeline_run_id": pipeline_run_id,
            "stage_id": stage_id,
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "name": name,
        },
    )


async def emit_confirm_required(
    task_id: str,
    *,
    project_id: str,
    session_id: str,
    pipeline_run_id: str,
    stage_id: str,
    stage_name: str,
    artifact_id: str | None,
    artifact_name: str | None,
) -> None:
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.CONFIRM_REQUIRED,
        {
            "task_id": task_id,
            "project_id": project_id,
            "session_id": session_id,
            "pipeline_run_id": pipeline_run_id,
            "stage_id": stage_id,
            "stage_name": stage_name,
            "artifact_id": artifact_id,
            "artifact_name": artifact_name,
        },
    )


async def emit_confirm_resolved(
    task_id: str,
    *,
    project_id: str,
    session_id: str,
    pipeline_run_id: str,
    stage_id: str,
    action: str,
) -> None:
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.CONFIRM_RESOLVED,
        {
            "task_id": task_id,
            "project_id": project_id,
            "session_id": session_id,
            "pipeline_run_id": pipeline_run_id,
            "stage_id": stage_id,
            "action": action,
        },
    )


async def emit_sub_task_created(task_id: str, sub_task_id: str, description: str) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SUB_TASK_CREATED,
        {"sub_task_id": sub_task_id, "description": description},
    )


async def emit_bid_received(task_id: str, agent_id: str, confidence: float) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.BID_RECEIVED,
        {"agent_id": agent_id, "confidence": confidence},
    )


# ── Thinking 事件 ─────────────────────────────────────────────

async def emit_thinking_start(task_id: str) -> None:
    await get_sse_manager().publish(task_id, SSEEventTypes.THINKING_START, {})


async def emit_thinking_delta(task_id: str, delta: str) -> None:
    await get_sse_manager().publish(task_id, SSEEventTypes.THINKING_DELTA, {"delta": delta})


async def emit_thinking_end(task_id: str, duration_ms: int) -> None:
    await get_sse_manager().publish(task_id, SSEEventTypes.THINKING_END, {"duration_ms": duration_ms})


# ── 沙箱代码执行事件 ──────────────────────────────────────────

async def emit_sandbox_executing(task_id: str, code: str) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_EXECUTING, {"code": code},
    )


async def emit_sandbox_completed(task_id: str, exit_code: int, duration_ms: int) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_COMPLETED,
        {"exit_code": exit_code, "duration_ms": duration_ms},
    )


async def emit_sandbox_timeout(task_id: str, timeout_seconds: int) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_TIMEOUT,
        {"timeout_seconds": timeout_seconds},
    )


# ── 沙箱生命周期事件（内部保留）────────────────────────────────

async def emit_sandbox_created(task_id: str, sandbox_id: str, template_id: str = "") -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_CREATED,
        {"sandbox_id": sandbox_id, "template_id": template_id},
    )


async def emit_sandbox_connected(task_id: str, sandbox_id: str, host: str = "", port: int = 0) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_CONNECTED,
        {"sandbox_id": sandbox_id, "host": host, "port": port},
    )


async def emit_sandbox_code_executing(task_id: str, sandbox_id: str, code_preview: str = "") -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_EXECUTING,
        {"sandbox_id": sandbox_id, "code": code_preview[:200]},
    )


async def emit_sandbox_code_completed(
    task_id: str, sandbox_id: str, exit_code: int = 0, duration_ms: int = 0
) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_COMPLETED,
        {"sandbox_id": sandbox_id, "exit_code": exit_code, "duration_ms": duration_ms},
    )


async def emit_sandbox_paused(task_id: str, sandbox_id: str) -> None:
    await get_sse_manager().publish(task_id, SSEEventTypes.SANDBOX_PAUSED, {"sandbox_id": sandbox_id})


async def emit_sandbox_destroyed(task_id: str, sandbox_id: str) -> None:
    await get_sse_manager().publish(task_id, SSEEventTypes.SANDBOX_DESTROYED, {"sandbox_id": sandbox_id})


async def emit_sandbox_timeout_legacy(task_id: str, sandbox_id: str, reason: str = "") -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_TIMEOUT,
        {"sandbox_id": sandbox_id, "reason": reason},
    )
