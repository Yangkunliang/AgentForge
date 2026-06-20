"""Harness Layer 5: Executor - 任务执行器和 Contract Net 协议"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Awaitable

if TYPE_CHECKING:
    from agent_forge.bus import MessagePublisher, BidResponseCollector
    from agent_forge.harness import AgentRegistry, GovernanceManager
    from agent_forge.models import Task, SubTask

logger = logging.getLogger("agent_forge.harness.executor")


class BidResult:
    """竞标结果"""

    def __init__(
        self,
        agent_id: str,
        confidence: float,
        estimated_time_ms: int,
    ):
        self.agent_id = agent_id
        self.confidence = confidence
        self.estimated_time_ms = estimated_time_ms


class TaskExecutor:
    """任务执行器"""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        governance_manager: GovernanceManager,
        publisher: MessagePublisher,
        bid_collector: BidResponseCollector,
    ):
        self.agent_registry = agent_registry
        self.governance = governance_manager
        self.publisher = publisher
        self.bid_collector = bid_collector

    async def execute_task(self, task: Task) -> dict:
        """执行任务（Contract Net 协议）"""
        logger.info(f"Executing task {task.id}")

        # 1. 分解任务为子任务
        sub_tasks = await self._decompose_task(task)
        logger.info(f"Decomposed task {task.id} into {len(sub_tasks)} sub_tasks")

        # 2. 并行执行子任务
        results = await asyncio.gather(
            *[self._execute_sub_task(task, sub_task) for sub_task in sub_tasks],
            return_exceptions=True,
        )

        # 3. 汇总结果
        return {
            "task_id": task.id,
            "status": "completed",
            "sub_task_results": [r for r in results if not isinstance(r, Exception)],
            "errors": [str(r) for r in results if isinstance(r, Exception)],
        }

    async def _decompose_task(self, task: Task) -> list[dict]:
        """分解任务为子任务"""
        # 简化：按 capability 分解
        # 实际场景中可以使用 LLM 分解任务
        capabilities = ["code", "analysis", "search"]
        return [
            {
                "id": f"{task.id}-sub-{i}",
                "capability": cap,
                "description": f"处理 {cap} 相关任务",
            }
            for i, cap in enumerate(capabilities)
        ]

    async def _execute_sub_task(self, task: Task, sub_task: dict) -> dict:
        """执行单个子任务"""
        sub_task_id = sub_task["id"]
        capability = sub_task["capability"]

        # 1. 广播招标消息
        await self.publisher.publish_bid_announcement(
            task_id=task.id,
            sub_task_id=sub_task_id,
            description=sub_task["description"],
            required_capabilities=[capability],
            deadline_ms=5000,
        )

        # 2. 收集竞标
        bids = await self.bid_collector.wait_for_responses(
            sub_task_id=sub_task_id,
            deadline_ms=5000,
            min_responses=1,
        )

        if not bids:
            logger.warning(f"No bids received for sub_task {sub_task_id}")
            return {"sub_task_id": sub_task_id, "status": "no_bids"}

        # 3. 选择最佳 Agent（最高 confidence）
        best_bid = max(bids, key=lambda b: b["confidence"])
        selected_agent_id = best_bid["agent_id"]

        logger.info(f"Selected agent {selected_agent_id} for sub_task {sub_task_id}")

        # 4. 发布任务分配
        await self.publisher.publish_task_assignment(
            task_id=task.id,
            sub_task_id=sub_task_id,
            agent_id=selected_agent_id,
            description=sub_task["description"],
        )

        return {
            "sub_task_id": sub_task_id,
            "agent_id": selected_agent_id,
            "confidence": best_bid["confidence"],
            "status": "assigned",
        }


class ContractNetProtocol:
    """Contract Net 协议实现"""

    def __init__(
        self,
        publisher: MessagePublisher,
        bid_collector: BidResponseCollector,
    ):
        self.publisher = publisher
        self.bid_collector = bid_collector

    async def announce_task(
        self,
        task_id: str,
        sub_task_id: str,
        description: str,
        required_capabilities: list[str],
        deadline_ms: int = 5000,
    ) -> None:
        """发布招标公告"""
        await self.publisher.publish_bid_announcement(
            task_id=task_id,
            sub_task_id=sub_task_id,
            description=description,
            required_capabilities=required_capabilities,
            deadline_ms=deadline_ms,
        )

    async def submit_bid(
        self,
        task_id: str,
        sub_task_id: str,
        agent_id: str,
        confidence: float,
        estimated_time_ms: int,
    ) -> None:
        """提交竞标"""
        await self.publisher.publish_bid_response(
            task_id=task_id,
            sub_task_id=sub_task_id,
            agent_id=agent_id,
            confidence=confidence,
            estimated_time_ms=estimated_time_ms,
        )

    async def collect_bids(
        self,
        sub_task_id: str,
        deadline_ms: int,
        min_responses: int = 1,
    ) -> list[dict]:
        """收集竞标响应"""
        return await self.bid_collector.wait_for_responses(
            sub_task_id=sub_task_id,
            deadline_ms=deadline_ms,
            min_responses=min_responses,
        )

    async def select_best_agent(self, bids: list[dict]) -> str | None:
        """选择最佳 Agent"""
        if not bids:
            return None

        # 按 confidence 排序，选择最高的
        sorted_bids = sorted(bids, key=lambda b: b["confidence"], reverse=True)
        return sorted_bids[0]["agent_id"]

    async def assign_task(
        self,
        task_id: str,
        sub_task_id: str,
        agent_id: str,
        description: str,
        context: dict | None = None,
    ) -> None:
        """分配任务给选中 Agent"""
        await self.publisher.publish_task_assignment(
            task_id=task_id,
            sub_task_id=sub_task_id,
            agent_id=agent_id,
            description=description,
            context=context,
        )