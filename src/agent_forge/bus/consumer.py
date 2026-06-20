"""RabbitMQ 消息消费"""

from __future__ import annotations

import asyncio
import json
import logging

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractQueue, AbstractIncomingMessage

logger = logging.getLogger("agent_forge.bus")


class MessageConsumer:
    """消息消费者"""

    def __init__(self, channel: AbstractChannel):
        self.channel = channel
        self.orchestrator_queue: AbstractQueue | None = None
        self.dlq_queue: AbstractQueue | None = None
        self._consumers: dict[str, asyncio.Task] = {}

    async def setup(self) -> None:
        """获取已声明的 Queue"""
        self.orchestrator_queue = await self.channel.get_queue("orchestrator.inbox")
        self.dlq_queue = await self.channel.get_queue("task.dlq")

    async def consume_orchestrator_inbox(
        self,
        callback: callable,
        queue_name: str = "orchestrator.inbox",
    ) -> None:
        """消费 orchestrator.inbox 队列的消息"""
        queue = await self.channel.get_queue(queue_name)

        async def process_message(message: AbstractIncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    message_type = data.get("message_type")
                    logger.debug(f"Received message: {message_type}")

                    await callback(data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # 消息会被拒绝并进入死信队列

        await queue.consume(process_message)
        logger.info(f"Started consuming queue: {queue_name}")

    async def consume_dead_letter_queue(
        self,
        callback: callable,
    ) -> None:
        """消费死信队列的消息"""
        async def process_message(message: AbstractIncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    logger.warning(f"Processing dead letter: {data.get('message_type')}")

                    await callback(data)
                except Exception as e:
                    logger.error(f"Error processing dead letter: {e}")

        await self.dlq_queue.consume(process_message)
        logger.info("Started consuming dead letter queue")

    async def stop_consuming(self) -> None:
        """停止所有消费者"""
        for task in self._consumers.values():
            task.cancel()
        self._consumers.clear()
        logger.info("Stopped all consumers")


class BidResponseCollector:
    """竞标响应收集器"""

    def __init__(self):
        self.responses: dict[str, list[dict]] = {}  # sub_task_id -> list of responses
        self._locks: dict[str, asyncio.Lock] = {}

    async def add_response(self, sub_task_id: str, response: dict) -> None:
        """添加竞标响应"""
        if sub_task_id not in self._locks:
            self._locks[sub_task_id] = asyncio.Lock()

        async with self._locks[sub_task_id]:
            if sub_task_id not in self.responses:
                self.responses[sub_task_id] = []
            self.responses[sub_task_id].append(response)
            logger.debug(f"Added bid response for sub_task {sub_task_id}: {response.get('agent_id')}")

    async def get_responses(self, sub_task_id: str) -> list[dict]:
        """获取指定子任务的竞标响应"""
        async with self._locks.get(sub_task_id, asyncio.Lock()):
            return self.responses.get(sub_task_id, [])

    async def clear_responses(self, sub_task_id: str) -> None:
        """清除指定子任务的竞标响应"""
        async with self._locks.get(sub_task_id, asyncio.Lock()):
            if sub_task_id in self.responses:
                del self.responses[sub_task_id]
            logger.debug(f"Cleared bid responses for sub_task {sub_task_id}")

    async def wait_for_responses(
        self,
        sub_task_id: str,
        deadline_ms: int,
        min_responses: int = 1,
    ) -> list[dict]:
        """等待竞标响应（直到 deadline 或达到最小数量）"""
        deadline_seconds = deadline_ms / 1000
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= deadline_seconds:
                logger.info(f"Deadline reached for sub_task {sub_task_id}")
                break

            responses = await self.get_responses(sub_task_id)
            if len(responses) >= min_responses:
                logger.info(f"Received {len(responses)} responses for sub_task {sub_task_id}")
                break

            # 等待一小段时间再检查
            await asyncio.sleep(0.1)

        return await self.get_responses(sub_task_id)