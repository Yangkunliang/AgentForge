"""AgentResolver tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.agents.resolver import SYSTEM_AGENT_PROFILE_ID, resolve_agent_profile
from agent_forge.models import Agent
from agent_forge.pipeline.catalog import get_stage_definition


@pytest.mark.asyncio
async def test_agent_resolver_selects_active_agent_by_stage_selector(
    db_session: AsyncSession,
):
    inactive = Agent(
        id=str(uuid.uuid4()),
        name=f"inactive-researcher-{uuid.uuid4()}",
        capabilities=["research"],
        model="gpt-4",
        status="inactive",
    )
    active = Agent(
        id=str(uuid.uuid4()),
        name=f"active-researcher-{uuid.uuid4()}",
        capabilities=["research"],
        model="claude-3-sonnet",
        status="active",
    )
    db_session.add_all([inactive, active])
    await db_session.commit()

    stage = get_stage_definition("bug_fix", "locate")
    profile = await resolve_agent_profile(db_session, stage_definition=stage)

    assert profile.id == active.id
    assert profile.name == active.name
    assert profile.source == "stage_default"
    assert profile.model_name == "claude-3-sonnet"


@pytest.mark.asyncio
async def test_agent_resolver_falls_back_to_system_profile_without_active_match(
    db_session: AsyncSession,
):
    inactive = Agent(
        id=str(uuid.uuid4()),
        name=f"inactive-coder-{uuid.uuid4()}",
        capabilities=["code_generation"],
        model="gpt-4",
        status="inactive",
    )
    db_session.add(inactive)
    await db_session.commit()

    stage = get_stage_definition("new_feature", "backend_dev")
    profile = await resolve_agent_profile(
        db_session,
        stage_definition=stage,
        fallback_agent_name="CodeSoul",
    )

    assert profile.id == SYSTEM_AGENT_PROFILE_ID
    assert profile.name == "CodeSoul"
    assert profile.source == "system_default"
