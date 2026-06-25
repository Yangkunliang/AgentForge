"""Embedding task consumer — RabbitMQ 异步生成 embedding"""

from __future__ import annotations

import json
import logging

from agent_forge.config import settings
from agent_forge.database import async_session_factory
from agent_forge.memory.embedder import chunk_text, embed
from agent_forge.models import SemanticEntry

logger = logging.getLogger("agent_forge.memory.tasks")


async def process_embedding_task(task_payload: dict) -> bool:
    """处理单条 embedding 生成任务

    Args:
        task_payload: {"semantic_entry_id": str, "content": str, "model": str | None}

    Returns:
        是否成功
    """
    entry_id = task_payload["semantic_entry_id"]
    content = task_payload["content"]
    model = task_payload.get("model")

    async with async_session_factory() as db:
        try:
            from sqlalchemy import select

            result = await db.execute(
                select(SemanticEntry).where(SemanticEntry.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                logger.error("SemanticEntry %s not found", entry_id)
                return False

            if entry.embedding is not None:
                logger.info(
                    "SemanticEntry %s already has embedding, skipping", entry_id
                )
                return True

            chunks = chunk_text(content)
            if not chunks:
                logger.warning("Empty content for entry %s", entry_id)
                return True

            # 逐 chunk embedding 并取平均
            embeddings: list[list[float]] = []
            for chunk in chunks:
                try:
                    vec = embed(chunk, model=model)
                    if vec:
                        embeddings.append(vec)
                except Exception as e:
                    logger.warning("Chunk embedding failed: %s", e)

            if embeddings:
                dim = len(embeddings[0])
                avg = [
                    sum(e[i] for e in embeddings) / len(embeddings)
                    for i in range(dim)
                ]
                entry.embedding = avg
                await db.commit()
                logger.info(
                    "Generated embedding for entry %s (%d chunks, %d dims)",
                    entry_id, len(chunks), dim,
                )
                return True

            return False

        except Exception as e:
            await db.rollback()
            logger.error("Embedding task failed for entry %s: %s", entry_id, e)
            return False


def consume_rabbitmq_message(body: bytes) -> None:
    """RabbitMQ 消息消费者入口

    从 RabbitMQ 队列消费 embedding 生成任务。

    消息格式: {"semantic_entry_id": "...", "content": "...", "model": "..."}
    """
    try:
        task_payload = json.loads(body)
        # 注意：此函数是同步的，需要在异步上下文中调用
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            # 如果已经有 running loop，在新的 event loop 中执行
            asyncio.run(process_embedding_task(task_payload))
        except RuntimeError:
            # 没有 running loop，直接创建
            asyncio.run(process_embedding_task(task_payload))
    except Exception as e:
        logger.error("Failed to consume embedding task: %s", e)


async def enqueue_embedding_task(
    db, entry_id: str, content: str, model: str | None = None
) -> None:
    """将 embedding 生成任务入队（RabbitMQ）

    调用此函数将任务放入队列，由后台 consumer 异步处理。

    Args:
        db: SQLAlchemy session（用于记录状态）
        entry_id: 记忆条目 ID
        content: 记忆内容
        model: embedding 模型
    """
    # 此处集成 RabbitMQ pub/sub
    # 实际实现需 aio_pika 客户端
    message_body = json.dumps({
        "semantic_entry_id": entry_id,
        "content": content,
        "model": model or settings.embedding_model,
    })

    # TODO: 发送到 RabbitMQ embedding 队列
    logger.info("Enqueueing embedding task for entry %s", entry_id)
    # await publish_to_embedding_queue(message_body)
