"""Memory API routes — CRUD、混合搜索、会话消息、用户记忆"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from agent_forge.database import async_session_factory
from agent_forge.memory import MemoryManager
from agent_forge.memory.embedder import chunk_text, embed
from agent_forge.models import User
from middleware.auth import get_current_user

logger = logging.getLogger("agent_forge.api.memory")

router = APIRouter(tags=["memory"])


# ── Request/Response Schemas ──────────────────────────────


class SemanticCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000, description="记忆内容")
    title: str = Field(default="", max_length=500, description="标题")
    category: str = Field(default="general", description="类别")
    task_id: str | None = Field(default=None, description="关联任务 ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")
    generate_embedding: bool = Field(default=True, description="是否生成 embedding")


class SemanticUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    title: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)


class SemanticEntryResponse(BaseModel):
    id: str
    user_id: str
    task_id: str | None
    title: str
    content: str
    category: str
    metadata: dict[str, Any]
    version: int
    deleted: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)
    category: str | None = Field(default=None)
    user_only: bool = Field(default=False, description="是否只搜索用户记忆")


class SearchResultResponse(BaseModel):
    id: str
    user_id: str
    task_id: str | None
    title: str
    content: str
    category: str
    score: float
    metadata: dict[str, Any]


class UserMemoryCreateRequest(BaseModel):
    category: str = Field(..., description="类别")
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Helper ────────────────────────────────────────────────


async def get_memory_manager() -> MemoryManager:
    """依赖注入：获取 MemoryManager 实例"""
    async with async_session_factory() as db:
        yield MemoryManager(db)


# ── Semantic Memory CRUD ──────────────────────────────────


@router.post("/semantic", response_model=SemanticEntryResponse)
async def create_semantic_memory(
    req: SemanticCreateRequest,
    current_user: User = Depends(get_current_user),
    mgr: MemoryManager = Depends(get_memory_manager),
) -> SemanticEntryResponse:
    """创建语义记忆"""
    user_id = current_user.id
    entry_id = await mgr.create_semantic_entry(
        user_id=user_id,
        content=req.content,
        title=req.title,
        category=req.category,
        task_id=req.task_id,
        metadata=req.metadata,
        generate_embedding=req.generate_embedding,
    )

    result = await mgr.get_semantic_entry(entry_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to retrieve created entry")

    return SemanticEntryResponse(
        id=result.id,
        user_id=result.user_id,
        task_id=result.task_id,
        title=result.title,
        content=result.content,
        category=result.category,
        metadata=result.extra_data if isinstance(result.extra_data, dict) else {},
        version=result.version,
        deleted=result.deleted,
        created_at=result.created_at.isoformat() if result.created_at else "",
        updated_at=result.updated_at.isoformat() if result.updated_at else "",
    )


@router.get("/semantic/{entry_id}", response_model=SemanticEntryResponse)
async def get_semantic_memory(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    mgr: MemoryManager = Depends(get_memory_manager),
) -> SemanticEntryResponse:
    """获取单条语义记忆"""
    user_id = current_user.id
    entry = await mgr.get_semantic_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    if entry.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return SemanticEntryResponse(
        id=entry.id,
        user_id=entry.user_id,
        task_id=entry.task_id,
        title=entry.title,
        content=entry.content,
        category=entry.category,
        metadata=entry.extra_data if isinstance(entry.extra_data, dict) else {},
        version=entry.version,
        deleted=entry.deleted,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
        updated_at=entry.updated_at.isoformat() if entry.updated_at else "",
    )


@router.put("/semantic/{entry_id}", response_model=SemanticEntryResponse)
async def update_semantic_memory(
    entry_id: str,
    req: SemanticUpdateRequest,
    current_user: User = Depends(get_current_user),
    mgr: MemoryManager = Depends(get_memory_manager),
) -> SemanticEntryResponse:
    """更新语义记忆"""
    user_id = current_user.id
    entry = await mgr.update_semantic_entry(
        entry_id=entry_id,
        content=req.content,
        title=req.title,
        category=req.category,
        metadata=req.metadata,
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    if entry.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return SemanticEntryResponse(
        id=entry.id,
        user_id=entry.user_id,
        task_id=entry.task_id,
        title=entry.title,
        content=entry.content,
        category=entry.category,
        metadata=entry.extra_data if isinstance(entry.extra_data, dict) else {},
        version=entry.version,
        deleted=entry.deleted,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
        updated_at=entry.updated_at.isoformat() if entry.updated_at else "",
    )


@router.delete("/semantic/{entry_id}")
async def delete_semantic_memory(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, str]:
    """软删除语义记忆"""
    user_id = current_user.id
    entry = await mgr.get_semantic_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    if entry.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await mgr.delete_semantic_entry(entry_id)
    return {"status": "deleted", "id": entry_id}


@router.get("/semantic", response_model=list[SemanticEntryResponse])
async def list_semantic_memories(
    current_user: User = Depends(get_current_user),
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    mgr: MemoryManager = Depends(get_memory_manager),
) -> list[SemanticEntryResponse]:
    """列出用户的语义记忆"""
    user_id = current_user.id
    entries = await mgr.list_semantic_entries(
        user_id=user_id,
        category=category,
        limit=limit,
        offset=offset,
    )
    return [
        SemanticEntryResponse(
            id=e.id,
            user_id=e.user_id,
            task_id=e.task_id,
            title=e.title,
            content=e.content,
            category=e.category,
            metadata=e.extra_data if isinstance(e.extra_data, dict) else {},
            version=e.version,
            deleted=e.deleted,
            created_at=e.created_at.isoformat() if e.created_at else "",
            updated_at=e.updated_at.isoformat() if e.updated_at else "",
        )
        for e in entries
    ]


# ── Hybrid Search ─────────────────────────────────────────


@router.post("/search", response_model=list[SearchResultResponse])
async def search_memories(
    req: SearchRequest,
    current_user: User = Depends(get_current_user),
    mgr: MemoryManager = Depends(get_memory_manager),
) -> list[SearchResultResponse]:
    """混合搜索：向量 + 全文"""
    user_id = current_user.id
    results = await mgr.search(
        query=req.query,
        user_id=user_id,
        limit=req.limit,
        category=req.category,
    )
    return [
        SearchResultResponse(
            id=r.id,
            user_id=r.user_id,
            task_id=r.task_id,
            title=r.title,
            content=r.content,
            category=r.category,
            score=r.score,
            metadata=r.metadata,
        )
        for r in results
    ]


# ── User Memory ──────────────────────────────────────────


@router.get("/user/{user_id_path}/memories")
async def get_user_memories(
    user_id_path: str,
    current_user: User = Depends(get_current_user),
    mgr: MemoryManager = Depends(get_memory_manager),
) -> list[dict[str, Any]]:
    """获取用户记忆列表"""
    user_id = user_id_path
    # Verify the requested user matches the authenticated user (defense in depth)
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    memories = await mgr.get_user_memories(user_id)
    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "category": m.category,
            "content": m.content,
            "metadata": m.extra_data if isinstance(m.extra_data, dict) else {},
            "created_at": m.created_at.isoformat() if m.created_at else "",
            "updated_at": m.updated_at.isoformat() if m.updated_at else "",
        }
        for m in memories
    ]


@router.put("/user/{user_id_path}/memories")
async def upsert_user_memory(
    user_id_path: str,
    req: UserMemoryCreateRequest,
    current_user: User = Depends(get_current_user),
    mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """更新或创建用户记忆"""
    user_id = user_id_path
    # Verify the requested user matches the authenticated user (defense in depth)
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    entry = await mgr.update_user_memory(
        user_id=user_id,
        category=req.category,
        content=req.content,
        metadata=req.metadata,
    )
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "category": entry.category,
        "content": entry.content,
        "metadata": entry.extra_data if isinstance(entry.extra_data, dict) else {},
        "created_at": entry.created_at.isoformat() if entry.created_at else "",
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else "",
    }
