"""SSE 流式输出 API"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

logger = logging.getLogger("agent_forge.api.sse")

sse_router = APIRouter(prefix="/sse", tags=["sse"])


class SSEEventTypes:
    """SSE 事件类型"""

    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SUB_TASK_CREATED = "sub_task_created"
    SUB_TASK_COMPLETED = "sub_task_completed"
    BID_RECEIVED = "bid_received"
    AGENT_ASSIGNED = "agent_assigned"
    LLM_RESPONSE = "llm_response"
    ERROR = "error"
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

        event = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
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
                except asyncio.TimeoutError:
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


async def emit_task_started(task_id: str, trace_id: str) -> None:
    """发射任务开始事件"""
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.TASK_STARTED,
        {
            "task_id": task_id,
            "trace_id": trace_id,
        },
    )


async def emit_task_completed(task_id: str, result: dict) -> None:
    """发射任务完成事件"""
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.TASK_COMPLETED,
        {
            "task_id": task_id,
            "content": result.get("content", ""),
        },
    )


async def emit_task_failed(task_id: str, error: str) -> None:
    """发射任务失败事件"""
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.TASK_FAILED,
        {
            "task_id": task_id,
            "error": error,
        },
    )


async def emit_sub_task_created(task_id: str, sub_task_id: str, description: str) -> None:
    """发射子任务创建事件"""
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.SUB_TASK_CREATED,
        {
            "sub_task_id": sub_task_id,
            "description": description,
        },
    )


async def emit_bid_received(task_id: str, agent_id: str, confidence: float) -> None:
    """发射竞标收到事件"""
    await get_sse_manager().publish(
        task_id,
        SSEEventTypes.BID_RECEIVED,
        {
            "agent_id": agent_id,
            "confidence": confidence,
        },
    )