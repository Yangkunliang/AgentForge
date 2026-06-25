"""Harness Layer 6: Memory - 短期记忆、长期记忆、审计日志

.. deprecated::
    此模块已被新的记忆系统替代。新的记忆系统位于
    ``src/agent_forge/memory/`` 目录，提供 4 层记忆架构
    （Working/Episodic/Semantic/User），支持语义搜索、
    向量 embedding、用户级记忆等能力。

    迁移指引：
    - 使用 ``from agent_forge.memory import MemoryManager``
    - 使用 ``from agent_forge.memory.embedder import embed, chunk_text``
    - 使用 ``from agent_forge.memory.retriever import MemoryRetriever``
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from agent_forge.models import AuditLog, MemoryEntry, Task

logger = logging.getLogger("agent_forge.harness.memory")


class Message:
    """对话消息"""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime | None = None,
    ):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


class Memory:
    """记忆管理器"""

    def __init__(self):
        # 短期记忆：task_id -> list[Message]
        self._short_term: dict[str, list[Message]] = {}

    def add_message(self, task_id: str, message: Message) -> None:
        """添加短期记忆消息"""
        if task_id not in self._short_term:
            self._short_term[task_id] = []
        self._short_term[task_id].append(message)
        logger.debug(f"Added message to short-term memory for task {task_id}")

    def get_history(self, task_id: str) -> list[Message]:
        """获取短期记忆历史"""
        return self._short_term.get(task_id, [])

    def clear_history(self, task_id: str) -> None:
        """清除短期记忆"""
        if task_id in self._short_term:
            del self._short_term[task_id]
            logger.debug(f"Cleared short-term memory for task {task_id}")


class LongTermMemory:
    """长期记忆管理器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_task_result(self, task_id: str, content: str, memory_type: str = "task_result") -> None:
        """保存任务结果到长期记忆"""
        from agent_forge.models import MemoryEntry

        entry = MemoryEntry(
            id=self._generate_id(),
            task_id=task_id,
            content=content,
            type=memory_type,
        )
        self.db.add(entry)
        await self.db.commit()
        logger.info(f"Saved long-term memory for task {task_id}")

    async def get_task_memory(self, task_id: str) -> list[dict]:
        """获取任务的长期记忆"""
        from agent_forge.models import MemoryEntry

        result = await self.db.execute(
            select(MemoryEntry).where(MemoryEntry.task_id == task_id)
        )
        entries = result.scalars().all()
        return [
            {
                "id": entry.id,
                "content": entry.content,
                "type": entry.type,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ]

    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())


class AuditLogger:
    """审计日志管理器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        resource: str,
        user_id: str,
        trace_id: str,
        status: str,
        degraded: bool = False,
        details: dict | None = None,
    ) -> None:
        """记录审计日志"""
        from agent_forge.models import AuditLog

        log_entry = AuditLog(
            id=self._generate_id(),
            action=action,
            resource=resource,
            user_id=user_id,
            trace_id=trace_id,
            status=status,
            degraded=degraded,
        )
        self.db.add(log_entry)
        await self.db.commit()
        logger.info(
            f"Audit log: action={action}, resource={resource}, "
            f"user_id={user_id}, trace_id={trace_id}, "
            f"status={status}, degraded={degraded}"
        )

    async def log_task_started(self, task_id: str, user_id: str, trace_id: str) -> None:
        """记录任务开始"""
        await self.log(
            action="task_started",
            resource="task",
            user_id=user_id,
            trace_id=trace_id,
            status="started",
        )

    async def log_task_completed(self, task_id: str, user_id: str, trace_id: str) -> None:
        """记录任务完成"""
        await self.log(
            action="task_completed",
            resource="task",
            user_id=user_id,
            trace_id=trace_id,
            status="completed",
        )

    async def log_task_failed(
        self,
        task_id: str,
        user_id: str,
        trace_id: str,
        error: str,
    ) -> None:
        """记录任务失败"""
        await self.log(
            action="task_failed",
            resource="task",
            user_id=user_id,
            trace_id=trace_id,
            status="failed",
            details={"error": error},
        )

    async def log_agent_execution(
        self,
        task_id: str,
        agent_id: str,
        user_id: str,
        trace_id: str,
        status: str,
    ) -> None:
        """记录 Agent 执行"""
        await self.log(
            action="agent_execution",
            resource="agent",
            user_id=user_id,
            trace_id=trace_id,
            status=status,
            details={"agent_id": agent_id, "task_id": task_id},
        )

    async def log_degraded_execution(
        self,
        task_id: str,
        user_id: str,
        trace_id: str,
        reason: str,
    ) -> None:
        """记录降级执行"""
        await self.log(
            action="degraded_execution",
            resource="task",
            user_id=user_id,
            trace_id=trace_id,
            status="degraded",
            degraded=True,
            details={"reason": reason},
        )

    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())


# 全局实例
_global_memory: Memory | None = None


def get_memory() -> Memory:
    """获取全局短期记忆管理器"""
    global _global_memory
    if _global_memory is None:
        _global_memory = Memory()
    return _global_memory