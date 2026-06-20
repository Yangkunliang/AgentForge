"""Harness Layer 2: Router - 任务路由和 trace_id 初始化"""

from __future__ import annotations

import logging
import uuid

from agent_forge.models import Task

logger = logging.getLogger("agent_forge.harness.router")


class Router:
    """任务路由器"""

    def route_task(self, task: Task) -> str:
        """路由任务到编排器，初始化 trace_id 上下文"""
        # 1. 初始化 trace_id（如果不存在）
        if not task.trace_id:
            task.trace_id = str(uuid.uuid4())
            logger.info(f"Initialized trace_id for task {task.id}: {task.trace_id}")

        # 2. 路由到 TaskOrchestrator（这里返回 trace_id，实际路由逻辑在 Executor 中实现）
        logger.info(f"Routing task {task.id} to orchestrator with trace_id {task.trace_id}")

        return task.trace_id

    def route_to_orchestrator(self, task: Task) -> dict:
        """准备任务数据发送到编排器"""
        return {
            "task_id": task.id,
            "user_id": task.user_id,
            "description": task.description,
            "priority": task.priority.value if hasattr(task.priority, "value") else task.priority,
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "trace_id": task.trace_id,
        }


def route_task(task: Task) -> str:
    """路由任务（便捷函数）"""
    router = Router()
    return router.route_task(task)