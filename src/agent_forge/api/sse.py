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
    LLM_RESPONSE = "llm_response"          # 最终文字 chunk（非 thinking）

    # ── Thinking 过程（用户感知）──────────────────────────────
    THINKING_START = "thinking_start"       # thinking 块开始，data: {}
    THINKING_DELTA = "thinking_delta"       # thinking 增量文字，data: {delta: str}
    THINKING_END   = "thinking_end"         # thinking 块结束，data: {duration_ms: int}

    # ── 工具调用（用户感知）───────────────────────────────────
    TOOL_CALL_START = "tool_call_start"     # data: {tool_name, arguments, tool_call_id}
    TOOL_CALL_END   = "tool_call_end"       # data: {tool_name, arguments, tool_call_id, result}

    # ── 沙箱代码执行（用户感知）──────────────────────────────
    SANDBOX_EXECUTING = "sandbox_executing"  # 开始执行代码，data: {code: str}
    SANDBOX_COMPLETED = "sandbox_completed"  # 执行完成，data: {exit_code, duration_ms}
    SANDBOX_TIMEOUT   = "sandbox_timeout"    # 执行超时，data: {timeout_seconds: int}

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
        # task_id -> list of queues
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """订阅任务事件"""
        if task_id not in self._locks:
            self._locks[task_id] = asyncio.Lock()

        queue = asyncio.Queue()
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(queue)
        logger.debug(f"New subscriber for task {task_id}")
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """取消订阅"""
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
                logger.debug(f"Removed subscriber for task {task_id}")
            except ValueError:
                pass

    async def publish(self, task_id: str, event_type: str, data: dict) -> None:
        """发布事件到所有订阅者"""
        if task_id not in self._subscribers:
            return

        event = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        for queue in self._subscribers[task_id]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"Queue full for task {task_id}, dropping event")

    async def stream_events(self, task_id: str) -> AsyncGenerator[str, None]:
        """流式事件生成器"""
        queue = self.subscribe(task_id)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield event
                except TimeoutError:
                    # 发送心跳
                    yield f"event: {SSEEventTypes.HEARTBEAT}\ndata: {{}}\n\n"
        except GeneratorExit:
            pass
        finally:
            self.unsubscribe(task_id, queue)


# 全局 SSE 管理器
_global_sse_manager: SSEManager | None = None


def get_sse_manager() -> SSEManager:
    """获取全局 SSE 管理器"""
    global _global_sse_manager
    if _global_sse_manager is None:
        _global_sse_manager = SSEManager()
    return _global_sse_manager


@sse_router.get("/tasks/{task_id}/stream")
async def stream_task_events(task_id: str):
    """流式获取任务事件"""
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
    """发布任务事件（内部使用）"""
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
    """LLM 开始 thinking 块"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.THINKING_START, {},
    )


async def emit_thinking_delta(task_id: str, delta: str) -> None:
    """thinking 增量文字（流式）"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.THINKING_DELTA, {"delta": delta},
    )


async def emit_thinking_end(task_id: str, duration_ms: int) -> None:
    """LLM thinking 块结束"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.THINKING_END, {"duration_ms": duration_ms},
    )


# ── 沙箱代码执行事件 ──────────────────────────────────────────

async def emit_sandbox_executing(task_id: str, code: str) -> None:
    """沙箱开始执行代码（用户可见）"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_EXECUTING,
        {"code": code},
    )


async def emit_sandbox_completed(
    task_id: str, exit_code: int, duration_ms: int
) -> None:
    """沙箱代码执行完成（状态辅助，结果由 tool_call_end 携带）"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_COMPLETED,
        {"exit_code": exit_code, "duration_ms": duration_ms},
    )


async def emit_sandbox_timeout(task_id: str, timeout_seconds: int) -> None:
    """沙箱执行超时"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_TIMEOUT,
        {"timeout_seconds": timeout_seconds},
    )


# ── 沙箱生命周期事件（内部，保留供 REST API 等低层使用）────────

async def emit_sandbox_created(
    task_id: str, sandbox_id: str, template_id: str = ""
) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_CREATED,
        {"sandbox_id": sandbox_id, "template_id": template_id},
    )


async def emit_sandbox_connected(
    task_id: str, sandbox_id: str, host: str = "", port: int = 0
) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_CONNECTED,
        {"sandbox_id": sandbox_id, "host": host, "port": port},
    )


async def emit_sandbox_code_executing(
    task_id: str, sandbox_id: str, code_preview: str = ""
) -> None:
    """旧接口保留（被 CoderAgent 使用），内部转发到 SANDBOX_EXECUTING"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_EXECUTING,
        {"sandbox_id": sandbox_id, "code": code_preview[:200]},
    )


async def emit_sandbox_code_completed(
    task_id: str, sandbox_id: str, exit_code: int = 0, duration_ms: int = 0
) -> None:
    """旧接口保留（被 CoderAgent 使用），内部转发到 SANDBOX_COMPLETED"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_COMPLETED,
        {"sandbox_id": sandbox_id, "exit_code": exit_code, "duration_ms": duration_ms},
    )


async def emit_sandbox_paused(task_id: str, sandbox_id: str) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_PAUSED,
        {"sandbox_id": sandbox_id},
    )


async def emit_sandbox_destroyed(task_id: str, sandbox_id: str) -> None:
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_DESTROYED,
        {"sandbox_id": sandbox_id},
    )


async def emit_sandbox_timeout_legacy(task_id: str, sandbox_id: str, reason: str = "") -> None:
    """旧接口保留"""
    await get_sse_manager().publish(
        task_id, SSEEventTypes.SANDBOX_TIMEOUT,
        {"sandbox_id": sandbox_id, "reason": reason},
    )
