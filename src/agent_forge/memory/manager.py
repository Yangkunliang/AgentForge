"""MemoryManager — 记忆系统编排层

协调 4 层记忆：
- Working: 当前会话上下文（复用现有 Memory class）
- Episodic: 对话历史（复用 chat_messages 表）
- Semantic: 跨会话语义记忆（semantic_entries 表 + pgvector）
- User: 用户级偏好/项目上下文（user_memories 表）
"""

from __future__ import annotations

import logging
import inspect
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.harness.memory import Memory as WorkingMemory
from agent_forge.memory.embedder import embed, chunk_text
from agent_forge.memory.retriever import MemoryRetriever, MemoryResult
from agent_forge.models import SemanticEntry, UserMemory

logger = logging.getLogger("agent_forge.memory.manager")


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def _scalar_one_or_none(result):
    return await _maybe_await(result.scalar_one_or_none())


async def _scalars_all(result):
    scalars = await _maybe_await(result.scalars())
    rows = await _maybe_await(scalars.all())
    return list(rows)


class MemoryManager:
    """记忆系统编排器

    提供统一的记忆 CRUD 和检索接口，集成 embedding 生成、
    混合检索、用户记忆管理和 Agent 提示注入。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.working = WorkingMemory()
        self.retriever = MemoryRetriever(db)

    # ── Semantic Memory CRUD ────────────────────────────────

    async def create_semantic_entry(
        self,
        user_id: str,
        content: str,
        title: str = "",
        category: str = "general",
        task_id: str | None = None,
        metadata: dict | None = None,
        generate_embedding: bool = True,
    ) -> str:
        """创建语义记忆条目

        Args:
            user_id: 用户 ID
            content: 记忆内容
            title: 标题
            category: 类别
            task_id: 关联任务 ID
            metadata: 附加元数据
            generate_embedding: 是否异步生成 embedding

        Returns:
            创建的记忆条目 ID
        """
        import uuid

        entry_id = str(uuid.uuid4())
        entry = SemanticEntry(
            id=entry_id,
            user_id=user_id,
            task_id=task_id,
            title=title or content[:200],
            content=content,
            category=category,
            extra_data=metadata or {},
            version=1,
        )
        await _maybe_await(self.db.add(entry))
        await self.db.commit()

        # 生成 embedding（同步）
        if generate_embedding and content.strip():
            try:
                chunks = chunk_text(content)
                for chunk in chunks:
                    vec = embed(chunk)
                    if vec:
                        # 将第一条的 embedding 作为主 embedding
                        if entry.embedding is None:
                            entry.embedding = vec
                        else:
                            # 后续 chunk 的平均值作为 embedding
                            entry.embedding = [
                                (a + b) / 2
                                for a, b in zip(entry.embedding, vec)
                            ]
                await self.db.commit()
            except Exception as e:
                logger.error("Failed to generate embedding: %s", e)

        logger.info(
            "Created semantic entry %s for user %s (category=%s)",
            entry_id, user_id, category,
        )
        return entry_id

    async def update_semantic_entry(
        self,
        entry_id: str,
        content: str | None = None,
        title: str | None = None,
        category: str | None = None,
        metadata: dict | None = None,
    ) -> SemanticEntry | None:
        """更新语义记忆条目（soft delete + version++）"""
        result = await self.db.execute(
            select(SemanticEntry).where(
                SemanticEntry.id == entry_id,
                SemanticEntry.deleted == False,  # noqa: E712
            )
        )
        entry = await _scalar_one_or_none(result)
        if not entry:
            return None

        if content is not None:
            entry.content = content
            entry.version += 1
        if title is not None:
            entry.title = title
        if category is not None:
            entry.category = category
        if metadata is not None:
            entry.extra_data = metadata

        entry.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return entry

    async def delete_semantic_entry(self, entry_id: str) -> bool:
        """软删除语义记忆条目"""
        result = await self.db.execute(
            select(SemanticEntry).where(
                SemanticEntry.id == entry_id,
                SemanticEntry.deleted == False,  # noqa: E712
            )
        )
        entry = await _scalar_one_or_none(result)
        if not entry:
            return False

        entry.deleted = True
        entry.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def get_semantic_entry(self, entry_id: str) -> SemanticEntry | None:
        """获取单条语义记忆（未删除的）"""
        result = await self.db.execute(
            select(SemanticEntry).where(
                SemanticEntry.id == entry_id,
                SemanticEntry.deleted == False,  # noqa: E712
            )
        )
        return await _scalar_one_or_none(result)

    async def list_semantic_entries(
        self,
        user_id: str,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SemanticEntry]:
        """列出用户的语义记忆条目"""
        query = select(SemanticEntry).where(
            SemanticEntry.user_id == user_id,
            SemanticEntry.deleted == False,  # noqa: E712
        )
        if category:
            query = query.where(SemanticEntry.category == category)
        query = query.order_by(SemanticEntry.updated_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)  # type: ignore[no-untyped-call]
        return await _scalars_all(result)

    # ── User Memory CRUD ────────────────────────────────────

    async def get_or_create_user_memory(
        self,
        user_id: str,
        category: str,
        content: str = "",
    ) -> UserMemory:
        """获取或创建用户记忆（category 唯一约束）"""
        result = await self.db.execute(
            select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.category == category,
            )
        )
        entry = await _scalar_one_or_none(result)

        if entry:
            return entry

        import uuid
        entry = UserMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            category=category,
            content=content,
        )
        await _maybe_await(self.db.add(entry))
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def update_user_memory(
        self,
        user_id: str,
        category: str,
        content: str,
        metadata: dict | None = None,
    ) -> UserMemory:
        """更新用户记忆"""
        result = await self.db.execute(
            select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.category == category,
            )
        )
        entry = await _scalar_one_or_none(result)
        if not entry:
            import uuid
            entry = UserMemory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                category=category,
                content=content,
                extra_data=metadata or {},
            )
            await _maybe_await(self.db.add(entry))
        else:
            entry.content = content
            if metadata:
                entry.extra_data = metadata
            entry.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_user_memories(self, user_id: str) -> list[UserMemory]:
        """获取用户所有记忆"""
        result = await self.db.execute(
            select(UserMemory).where(UserMemory.user_id == user_id)
            .order_by(UserMemory.updated_at.desc())
        )
        return await _scalars_all(result)

    # ── Search ──────────────────────────────────────────────

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        category: str | None = None,
    ) -> list[MemoryResult]:
        """统一搜索接口

        在 semantic_entries + user_memories 中做混合检索。
        """
        return await self.retriever.hybrid_search(
            query=query,
            user_id=user_id,
            limit=limit,
            category=category,
            user_only=False,
        )

    # ── Agent Prompt Injection ──────────────────────────────

    async def prepare_task_context(self, task_id: str) -> str:
        """为任务准备上下文：检索相关记忆 + 用户偏好

        在 Agent 执行任务前调用，返回可注入到 prompt 的上下文字符串。
        """
        # 获取 task 信息（简化：通过 user_id 搜索）
        context_parts: list[str] = []

        # 从 episodic memory 获取最近的用户输入（chat_messages）
        user_inputs = await self._get_recent_user_inputs(task_id)
        if user_inputs:
            context_parts.append("=== Recent User Context ===")
            for inp in user_inputs:
                context_parts.append(f"- {inp}")

        # 从 semantic memory 获取相关记忆
        if user_inputs:
            last_input = user_inputs[-1]
            relevant = await self.search(
                query=last_input,
                user_id="placeholder",  # 需从 task 获取 user_id
                limit=3,
            )
            if relevant:
                context_parts.append("\n=== Relevant Past Memories ===")
                for m in relevant:
                    context_parts.append(f"- [{m.category}] {m.title}: {m.content[:200]}")

        # 从 user memory 获取偏好
        # TODO: 需要传入 user_id
        # user_prefs = await self.get_user_memories(user_id)

        if not context_parts:
            return ""

        return "\n\n".join(context_parts)

    # ── Episodic Memory (chat_messages) ─────────────────────

    async def _get_recent_user_inputs(self, task_id: str) -> list[str]:
        """从 chat_messages 获取最近的 user 输入"""
        from agent_forge.models import Message

        result = await self.db.execute(
            select(Message.content)
            .where(
                Message.role == "user",
                Message.task_id == task_id,
            )
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        rows = await _scalars_all(result)
        return list(reversed(rows))  # 按时间正序
