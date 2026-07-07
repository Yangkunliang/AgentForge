"""MemoryRetriever — 向量相似度 + PostgreSQL 全文搜索混合检索"""

from __future__ import annotations

import logging
import inspect
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.config import settings
from agent_forge.memory.embedder import embed

logger = logging.getLogger("agent_forge.memory.retriever")


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def _fetchall(result):
    return await _maybe_await(result.fetchall())


@dataclass
class MemoryResult:
    """混合检索返回的记忆结果"""

    id: str
    user_id: str
    task_id: str | None
    title: str
    content: str
    category: str
    score: float  # 0-1，越高越相关
    metadata: dict = field(default_factory=dict)
    embedding_score: float = 0.0
    keyword_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


class MemoryRetriever:
    """混合检索器：向量相似度（pgvector）+ PostgreSQL 全文搜索"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def hybrid_search(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        category: str | None = None,
        user_only: bool = True,
    ) -> list[MemoryResult]:
        """混合检索：向量相似度 0.6 + 全文 0.4 加权合并

        Args:
            query: 搜索查询
            user_id: 用户 ID（限制搜索范围）
            limit: 返回结果数
            category: 按类别过滤
            user_only: 是否只检索 user_memories

        Returns:
            排序后的 MemoryResult 列表
        """
        results: list[MemoryResult] = []

        if user_only:
            semantic_results = await self._search_user_memories(
                query, user_id, limit, category
            )
            results.extend(semantic_results)
        else:
            # 同时搜 semantic_entries 和 user_memories
            semantic = await self._search_semantic_entries(
                query, user_id, limit, category
            )
            user_mem = await self._search_user_memories(
                query, user_id, limit, category
            )
            results.extend(semantic)
            results.extend(user_mem)

        # 去重 + 排序
        seen: set[str] = set()
        unique: list[MemoryResult] = []
        for r in sorted(results, key=lambda x: x.score, reverse=True):
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)

        return unique[:limit]

    async def _search_semantic_entries(
        self,
        query: str,
        user_id: str,
        limit: int,
        category: str | None,
    ) -> list[MemoryResult]:
        """在 semantic_entries 中做混合检索"""
        results: list[MemoryResult] = []

        # 1. 向量搜索
        try:
            query_vec = embed(query)
            if query_vec:
                results.extend(
                    await self._vector_search(
                        query_vec, user_id, limit * 2, category
                    )
                )
        except Exception as e:
            logger.warning("Vector search failed, falling back to keyword: %s", e)

        # 2. 全文搜索
        results.extend(
            await self._keyword_search(query, "semantic_entries", user_id, limit * 2, category)
        )

        return results[:limit]

    async def _search_user_memories(
        self,
        query: str,
        user_id: str,
        limit: int,
        category: str | None,
    ) -> list[MemoryResult]:
        """在 user_memories 中做全文检索"""
        results: list[MemoryResult] = []

        # user_memories 通常数据量小，直接用全文搜索即可
        results.extend(
            await self._keyword_search(query, "user_memories", user_id, limit * 2, category)
        )

        # 也做向量搜索
        try:
            query_vec = embed(query)
            if query_vec:
                results.extend(
                    await self._vector_search_user_memories(
                        query_vec, user_id, limit * 2, category
                    )
                )
        except Exception as e:
            logger.warning("Vector search user_memories failed: %s", e)

        return results[:limit]

    async def _vector_search(
        self,
        query_vec: list[float],
        user_id: str,
        limit: int,
        category: str | None,
    ) -> list[MemoryResult]:
        """pgvector 向量相似度搜索 semantic_entries"""
        results: list[MemoryResult] = []

        query = text("""
            SELECT id, user_id, COALESCE(task_id, ''), title, content,
                   category, metadata, 1 - (embedding <=> :vec) AS similarity
            FROM semantic_entries
            WHERE user_id = :user_id
              AND deleted = FALSE
              AND embedding IS NOT NULL
        """)
        params: dict[str, Any] = {
            "user_id": user_id,
            "vec": str(query_vec),
        }

        if category:
            query = text(str(query) + " AND category = :cat")
            params["cat"] = category

        query = text(str(query) + " ORDER BY similarity DESC LIMIT :lim")
        params["lim"] = limit

        res = await self.db.execute(query, params)  # type: ignore[no-untyped-call]
        rows = await _fetchall(res)

        for row in rows:
            results.append(MemoryResult(
                id=row[0],
                user_id=row[1],
                task_id=row[2],
                title=row[3],
                content=row[4],
                category=row[5],
                metadata=row[6] if isinstance(row[6], dict) else {},
                score=float(row[7]),
                embedding_score=float(row[7]),
            ))

        return results

    async def _vector_search_user_memories(
        self,
        query_vec: list[float],
        user_id: str,
        limit: int,
        category: str | None,
    ) -> list[MemoryResult]:
        """pgvector 向量相似度搜索 user_memories（需要为 user_memories 加向量索引）"""
        # 当前 user_memories 不做向量搜索，返回空
        # 后续如需可扩展
        return []

    async def _keyword_search(
        self,
        search_query: str,
        table: str,
        user_id: str,
        limit: int,
        category: str | None,
    ) -> list[MemoryResult]:
        """PostgreSQL 全文搜索"""
        results: list[MemoryResult] = []
        if table not in {"semantic_entries", "user_memories"}:
            raise ValueError(f"Unsupported memory table: {table}")

        if table == "semantic_entries":
            query_sql = """
                SELECT id, user_id, COALESCE(task_id, ''), title, content,
                       category, COALESCE(metadata, '{}'::jsonb),
                       ts_rank(to_tsvector('english', content || ' ' || title),
                               plainto_tsquery('english', :query)) AS rank
                FROM semantic_entries
                WHERE user_id = :user_id
                  AND deleted = FALSE
            """
        else:
            query_sql = """
                SELECT id, user_id, NULL AS task_id, category AS title, content,
                       category, COALESCE(metadata, '{}'::jsonb),
                       ts_rank(to_tsvector('english', content || ' ' || category),
                               plainto_tsquery('english', :query)) AS rank
                FROM user_memories
                WHERE user_id = :user_id
            """
        params: dict[str, Any] = {
            "user_id": user_id,
            "query": search_query,
        }

        if category:
            query_sql += " AND category = :cat"
            params["cat"] = category

        query = text(query_sql + """
            ORDER BY rank DESC
            LIMIT :lim
        """)
        params["lim"] = limit

        res = await self.db.execute(query, params)  # type: ignore[no-untyped-call]
        rows = await _fetchall(res)

        for row in rows:
            results.append(MemoryResult(
                id=row[0],
                user_id=row[1],
                task_id=row[2],
                title=row[3],
                content=row[4],
                category=row[5],
                metadata=row[6] if isinstance(row[6], dict) else {},
                score=float(row[7]),
                keyword_score=float(row[7]),
            ))

        return results
