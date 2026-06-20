"""RabbitMQ 消息发布"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange

logger = logging.getLogger("agent_forge.bus")


class MessagePublisher:
    """消息发布器"""

    def __init__(self, channel: AbstractChannel):
        self.channel = channel
        self.broadcast_exchange: AbstractExchange | None = None
        self.direct_exchange: AbstractExchange | None = None

    async def setup(self) -> None:
        """获取已声明的 Exchange"""
        self.broadcast_exchange = await self.channel.get_exchange("task.broadcast")
        self.direct_exchange = await self.channel.get_exchange("task.direct")

    async def publish_bid_announcement(
        self,
        task_id: str,
        sub_task_id: str,
        description: str,
        required_capabilities: list[str],
        deadline_ms: int = 5000,
        trace_id: str | None = None,
    ) -> None:
        """发布招标公告（广播）"""
        message_data = {
            "message_type": "BID_ANNOUNCEMENT",
            "task_id": task_id,
            "sub_task_id": sub_task_id,
            "description": description,
            "required_capabilities": required_capabilities,
            "deadline_ms": deadline_ms,
            "trace_id": trace_id or task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        message = aio_pika.Message(
            body=json.dumps(message_data).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await self.broadcast_exchange.publish(message)
        logger.info(f"Published BID_ANNOUNCEMENT for task {task_id}, sub_task {sub_task_id}")

    async def publish_task_assignment(
        self,
        task_id: str,
        sub_task_id: str,
        agent_id: str,
        description: str,
        context: dict | None = None,
        trace_id: str | None = None,
    ) -> None:
        """发布任务分配（定向）"""
        message_data = {
            "message_type": "TASK_ASSIGNMENT",
            "task_id": task_id,
            "sub_task_id": sub_task_id,
            "agent_id": agent_id,
            "description": description,
            "context": context or {},
            "trace_id": trace_id or task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        message = aio_pika.Message(
            body=json.dumps(message_data).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        # routing_key: agent.{id}
        routing_key = f"agent.{agent_id}"
        await self.direct_exchange.publish(message, routing_key=routing_key)
        logger.info(f"Published TASK_ASSIGNMENT to agent {agent_id} for task {task_id}")

    async def publish_task_result(
        self,
        task_id: str,
        sub_task_id: str,
        agent_id: str,
        status: str,
        result: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        trace_id: str | None = None,
    ) -> None:
        """发布任务结果（定向）"""
        message_data = {
            "message_type": "TASK_RESULT",
            "task_id": task_id,
            "sub_task_id": sub_task_id,
            "agent_id": agent_id,
            "status": status,
            "result": result,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "trace_id": trace_id or task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        message = aio_pika.Message(
            body=json.dumps(message_data).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        # routing_key: orchestrator
        await self.direct_exchange.publish(message, routing_key="orchestrator")
        logger.info(f"Published TASK_RESULT from agent {agent_id} for task {task_id}")

    async def publish_bid_response(
        self,
        task_id: str,
        sub_task_id: str,
        agent_id: str,
        confidence: float,
        estimated_time_ms: int,
        trace_id: str | None = None,
    ) -> None:
        """发布竞标响应（定向）"""
        message_data = {
            "message_type": "BID_RESPONSE",
            "task_id": task_id,
            "sub_task_id": sub_task_id,
            "agent_id": agent_id,
            "confidence": confidence,
            "estimated_time_ms": estimated_time_ms,
            "trace_id": trace_id or task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        message = aio_pika.Message(
            body=json.dumps(message_data).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        # routing_key: orchestrator
        await self.direct_exchange.publish(message, routing_key="orchestrator")
        logger.info(f"Published BID_RESPONSE from agent {agent_id} for task {task_id}")