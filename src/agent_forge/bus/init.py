"""RabbitMQ 消息总线初始化"""

from __future__ import annotations

import logging

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue

logger = logging.getLogger("agent_forge.bus")


class RabbitMQInitializer:
    """RabbitMQ 消息总线初始化器"""

    EXCHANGE_BROADCAST = "task.broadcast"
    EXCHANGE_DIRECT = "task.direct"
    EXCHANGE_DLX = "task.dlx"

    QUEUE_ORCHESTRATOR_INBOX = "orchestrator.inbox"
    QUEUE_DLQ = "task.dlq"

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: AbstractChannel | None = None

        # Exchanges
        self.broadcast_exchange: AbstractExchange | None = None
        self.direct_exchange: AbstractExchange | None = None
        self.dlx_exchange: AbstractExchange | None = None

        # Queues
        self.orchestrator_queue: AbstractQueue | None = None
        self.dlq_queue: AbstractQueue | None = None

    async def connect(self) -> None:
        """建立 RabbitMQ 连接"""
        logger.info(f"Connecting to RabbitMQ: {self.connection_url}")
        self.connection = await aio_pika.connect_robust(self.connection_url)
        self.channel = await self.connection.channel()
        logger.info("RabbitMQ connection established")

    async def initialize(self) -> None:
        """初始化消息总线拓扑（幂等）"""
        if not self.channel:
            await self.connect()

        logger.info("Initializing RabbitMQ topology...")

        # 1. 声明 Exchanges
        await self._declare_exchanges()

        # 2. 声明 Queues
        await self._declare_queues()

        # 3. 绑定关系
        await self._bind_queues()

        logger.info("RabbitMQ topology initialized successfully")

    async def _declare_exchanges(self) -> None:
        """声明所有 Exchange"""
        # task.broadcast (fanout) - 用于广播招标消息
        self.broadcast_exchange = await self.channel.declare_exchange(
            self.EXCHANGE_BROADCAST,
            ExchangeType.FANOUT,
            durable=True,
        )
        logger.debug(f"Declared exchange: {self.EXCHANGE_BROADCAST}")

        # task.direct (direct) - 用于定向消息传递
        self.direct_exchange = await self.channel.declare_exchange(
            self.EXCHANGE_DIRECT,
            ExchangeType.DIRECT,
            durable=True,
        )
        logger.debug(f"Declared exchange: {self.EXCHANGE_DIRECT}")

        # task.dlx (direct) - 死信交换器
        self.dlx_exchange = await self.channel.declare_exchange(
            self.EXCHANGE_DLX,
            ExchangeType.DIRECT,
            durable=True,
        )
        logger.debug(f"Declared exchange: {self.EXCHANGE_DLX}")

    async def _declare_queues(self) -> None:
        """声明所有 Queue"""
        # orchestrator.inbox - 编排器接收队列（TTL 60s + 死信）
        self.orchestrator_queue = await self.channel.declare_queue(
            self.QUEUE_ORCHESTRATOR_INBOX,
            durable=True,
            arguments={
                "x-message-ttl": 60000,  # 60s TTL
                "x-dead-letter-exchange": self.EXCHANGE_DLX,
                "x-dead-letter-routing-key": "dlq",
            },
        )
        logger.debug(f"Declared queue: {self.QUEUE_ORCHESTRATOR_INBOX}")

        # task.dlq - 死信队列
        self.dlq_queue = await self.channel.declare_queue(
            self.QUEUE_DLQ,
            durable=True,
        )
        logger.debug(f"Declared queue: {self.QUEUE_DLQ}")

    async def _bind_queues(self) -> None:
        """绑定 Queue 到 Exchange"""
        # orchestrator.inbox 绑定到 task.direct (routing_key: orchestrator)
        await self.orchestrator_queue.bind(
            self.direct_exchange,
            routing_key="orchestrator",
        )
        logger.debug(f"Bound {self.QUEUE_ORCHESTRATOR_INBOX} to {self.EXCHANGE_DIRECT} with routing_key=orchestrator")

        # task.dlq 绑定到 task.dlx (routing_key: dlq)
        await self.dlq_queue.bind(
            self.dlx_exchange,
            routing_key="dlq",
        )
        logger.debug(f"Bound {self.QUEUE_DLQ} to {self.EXCHANGE_DLX} with routing_key=dlq")

    async def close(self) -> None:
        """关闭连接"""
        if self.connection:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")


async def initialize_rabbitmq(connection_url: str) -> RabbitMQInitializer:
    """初始化 RabbitMQ 消息总线（便捷函数）"""
    initializer = RabbitMQInitializer(connection_url)
    await initializer.initialize()
    return initializer