"""Resolve runtime AgentProfile for pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Agent
from agent_forge.pipeline.catalog import StageDefinition

SYSTEM_AGENT_PROFILE_ID = "system-default"
DEFAULT_MODEL_ROUTE_KEY = "default"

_SELECTOR_CAPABILITY_MAP: dict[str, tuple[str, ...]] = {
    "planner": ("planning", "requirements", "architecture", "documentation", "research"),
    "coder": ("code_generation", "code", "refactoring"),
    "designer": ("ui_design", "design", "frontend"),
    "reviewer": ("code_review", "review", "quality"),
    "tester": ("testing", "test"),
    "researcher": ("research", "analysis", "debugging"),
}


@dataclass(frozen=True)
class AgentProfile:
    """Stable runtime view of an Agent used by StageRuntime."""

    id: str
    name: str
    source: str
    capabilities: list[str]
    model_name: str | None = None
    default_model_route_key: str = DEFAULT_MODEL_ROUTE_KEY
    allowed_skill_names: list[str] | None = None

    def to_context(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "capabilities": self.capabilities,
            "model_name": self.model_name,
            "default_model_route_key": self.default_model_route_key,
            "allowed_skill_names": self.allowed_skill_names or [],
        }


async def resolve_agent_profile(
    db: AsyncSession,
    *,
    stage_definition: StageDefinition | None,
    user_override_agent_id: str | None = None,
    project_default_agent_id: str | None = None,
    fallback_agent_name: str = "CodeSoul",
) -> AgentProfile:
    """Resolve an AgentProfile using override -> project default -> stage default -> system default."""

    override = await _get_active_agent_by_id(db, user_override_agent_id)
    if override:
        return _profile_from_agent(override, "user_override")

    project_default = await _get_active_agent_by_id(db, project_default_agent_id)
    if project_default:
        return _profile_from_agent(project_default, "project_default")

    selector = stage_definition.default_agent_selector if stage_definition else None
    stage_agent = await _get_active_agent_by_selector(db, selector)
    if stage_agent:
        return _profile_from_agent(stage_agent, "stage_default")

    return AgentProfile(
        id=SYSTEM_AGENT_PROFILE_ID,
        name=fallback_agent_name or "CodeSoul",
        source="system_default",
        capabilities=[],
        model_name=None,
        default_model_route_key=stage_definition.model_route_key if stage_definition else DEFAULT_MODEL_ROUTE_KEY,
        allowed_skill_names=[],
    )


async def list_runtime_agent_candidates(
    db: AsyncSession,
    *,
    stage_selector: str | None = None,
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Agent)
        .where(Agent.status == "active")
        .order_by(Agent.created_at.asc(), Agent.name.asc())
    )
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "capabilities": list(agent.capabilities or []),
            "model": agent.model,
            "description": agent.description,
            "avatar_url": agent.avatar_url,
            "recommended": _agent_matches_selector(agent, stage_selector),
        }
        for agent in result.scalars().all()
    ]


async def _get_active_agent_by_id(db: AsyncSession, agent_id: str | None) -> Agent | None:
    if not agent_id:
        return None
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.status == "active")
    )
    return result.scalar_one_or_none()


async def _get_active_agent_by_selector(db: AsyncSession, selector: str | None) -> Agent | None:
    if not selector:
        return None

    candidates = _SELECTOR_CAPABILITY_MAP.get(selector, (selector,))
    result = await db.execute(
        select(Agent)
        .where(Agent.status == "active")
        .order_by(Agent.created_at.asc(), Agent.name.asc())
    )
    for agent in result.scalars().all():
        if _agent_matches_capabilities(agent, candidates):
            return agent
    return None


def _profile_from_agent(agent: Agent, source: str) -> AgentProfile:
    return AgentProfile(
        id=agent.id,
        name=agent.name,
        source=source,
        capabilities=list(agent.capabilities or []),
        model_name=agent.model,
        default_model_route_key=DEFAULT_MODEL_ROUTE_KEY,
        allowed_skill_names=[],
    )


def _agent_matches_selector(agent: Agent, selector: str | None) -> bool:
    if not selector:
        return False
    candidates = _SELECTOR_CAPABILITY_MAP.get(selector, (selector,))
    return _agent_matches_capabilities(agent, candidates)


def _agent_matches_capabilities(agent: Agent, candidates: tuple[str, ...]) -> bool:
    capabilities = set(agent.capabilities or [])
    return bool(capabilities.intersection(candidates))
