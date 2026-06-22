"""Agent 管理路由"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import get_async_session
from agent_forge.models import Agent, User, UserAgentSettings
from api.schemas.agent import AgentCreateRequest, AgentResponse, AgentUpdateRequest
from middleware.auth import get_current_user, require_permission

router = APIRouter()
logger = logging.getLogger("agent_forge")


def _agent_to_dict(agent: Agent) -> dict:
    """将 Agent 模型转为字典"""
    return {
        "id": agent.id,
        "name": agent.name,
        "capabilities": agent.capabilities or [],
        "model": agent.model,
        "status": agent.status,
        "description": agent.description,
        "avatar_url": agent.avatar_url,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
    }


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("admin")),
) -> dict:
    """创建 Agent（需 admin 权限）"""
    # 检查名称是否已存在
    result = await db.execute(select(Agent).where(Agent.name == body.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent name already exists")

    agent = Agent(
        id=str(uuid.uuid4()),
        name=body.name,
        capabilities=body.capabilities,
        model=body.model,
        description=body.description,
        avatar_url=body.avatar_url,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _agent_to_dict(agent)


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("read")),
    capability: str | None = Query(default=None, description="按能力过滤"),
    status_filter: str | None = Query(default=None, alias="status", description="按状态过滤"),
) -> list[dict]:
    """获取 Agent 列表（支持过滤）"""
    query = select(Agent)

    if status_filter:
        query = query.where(Agent.status == status_filter)

    result = await db.execute(query)
    agents = result.scalars().all()

    # capability 过滤在内存中进行（JSON 字段）
    if capability:
        agents = [a for a in agents if capability in (a.capabilities or [])]

    return [_agent_to_dict(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("read")),
) -> dict:
    """获取单个 Agent"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_to_dict(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: AgentUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("admin")),
) -> dict:
    """更新 Agent（需 admin 权限）"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return _agent_to_dict(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("admin")),
) -> None:
    """删除 Agent（需 admin 权限）"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(agent)
    await db.commit()


class AgentSettingsUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)


@router.get("/settings/me")
async def get_my_agent_settings(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前用户的 AI 助手设置（所有用户可用）"""
    result = await db.execute(
        select(UserAgentSettings).where(UserAgentSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return {"agent_name": "CodeSoul", "avatar_url": None}
    return {"agent_name": settings.agent_name, "avatar_url": settings.avatar_url}


@router.patch("/settings/me")
async def update_my_agent_settings(
    body: AgentSettingsUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """更新当前用户的 AI 助手设置（所有用户可用）"""
    result = await db.execute(
        select(UserAgentSettings).where(UserAgentSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserAgentSettings(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            agent_name=body.name or "CodeSoul",
            avatar_url=body.avatar_url,
        )
        db.add(settings)
    else:
        update_data = body.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return {"agent_name": settings.agent_name, "avatar_url": settings.avatar_url}
