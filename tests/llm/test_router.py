"""ModelRouter behavior tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.llm.router import resolve_model_route
from agent_forge.models import LLMCredential, LLMModelSetting, LLMProviderSetting, LLMRoute, User
from agent_forge.security.credentials import encrypt_secret


@pytest.mark.asyncio
async def test_model_router_resolves_database_route_and_decrypts_credential(
    db_session: AsyncSession,
    fake_user: User,
):
    provider_key = f"anthropic-{uuid.uuid4().hex[:8]}"
    model_key = f"anthropic/claude-3-5-sonnet-{uuid.uuid4().hex[:8]}"
    provider = LLMProviderSetting(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        provider_key=provider_key,
        name="Anthropic",
        base_url="https://api.anthropic.com",
        status="active",
    )
    model = LLMModelSetting(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        provider_id=provider.id,
        model_key=model_key,
        name="Claude 3.5 Sonnet",
        capabilities=["text", "code"],
        context_window=200000,
        status="active",
    )
    credential = LLMCredential(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        provider_id=provider.id,
        name="prod-key",
        encrypted_secret=encrypt_secret("sk-ant-secret-1234"),
        secret_hint="sk-ant...1234",
        active=True,
    )
    route = LLMRoute(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        route_key="review",
        name="Review Route",
        provider_id=provider.id,
        model_id=model.id,
        credential_id=credential.id,
        temperature=0.2,
        max_tokens=8192,
        timeout_seconds=45,
        fallback_route_keys=[],
        active=True,
    )
    db_session.add_all([provider, model, credential, route])
    await db_session.commit()

    resolved = await resolve_model_route(db_session, user_id=fake_user.id, requested_key="review")

    assert resolved.route_key == "review"
    assert resolved.source == "database"
    assert resolved.config.model == model_key
    assert resolved.config.temperature == 0.2
    assert resolved.config.max_tokens == 8192
    assert resolved.config.timeout == 45
    assert resolved.config.api_key == "sk-ant-secret-1234"
    assert resolved.config.api_base == "https://api.anthropic.com"
    assert resolved.to_context() == {
        "route_key": "review",
        "name": "Review Route",
        "source": "database",
        "provider_key": provider_key,
        "model_name": model_key,
        "credential_id": credential.id,
        "credential_name": "prod-key",
        "fallback_route_keys": [],
        "requested_route_key": "review",
    }


@pytest.mark.asyncio
async def test_model_router_uses_fallback_when_primary_route_is_unavailable(
    db_session: AsyncSession,
    fake_user: User,
):
    provider_key = f"openai-{uuid.uuid4().hex[:8]}"
    inactive_model_key = f"openai/gpt-4o-{uuid.uuid4().hex[:8]}"
    fallback_model_key = f"openai/gpt-4o-mini-{uuid.uuid4().hex[:8]}"
    provider = LLMProviderSetting(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        provider_key=provider_key,
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        status="active",
    )
    inactive_model = LLMModelSetting(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        provider_id=provider.id,
        model_key=inactive_model_key,
        name="GPT-4o",
        capabilities=["text"],
        context_window=128000,
        status="inactive",
    )
    fallback_model = LLMModelSetting(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        provider_id=provider.id,
        model_key=fallback_model_key,
        name="GPT-4o Mini",
        capabilities=["text"],
        context_window=128000,
        status="active",
    )
    primary_route = LLMRoute(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        route_key="primary",
        name="Primary Route",
        provider_id=provider.id,
        model_id=inactive_model.id,
        credential_id=None,
        temperature=0.4,
        max_tokens=2048,
        timeout_seconds=60,
        fallback_route_keys=["safe"],
        active=True,
    )
    fallback_route = LLMRoute(
        id=str(uuid.uuid4()),
        user_id=fake_user.id,
        route_key="safe",
        name="Safe Route",
        provider_id=provider.id,
        model_id=fallback_model.id,
        credential_id=None,
        temperature=0.1,
        max_tokens=1024,
        timeout_seconds=30,
        fallback_route_keys=[],
        active=True,
    )
    db_session.add_all([provider, inactive_model, fallback_model, primary_route, fallback_route])
    await db_session.commit()

    resolved = await resolve_model_route(db_session, user_id=fake_user.id, requested_key="primary")

    assert resolved.route_key == "safe"
    assert resolved.source == "fallback"
    assert resolved.requested_route_key == "primary"
    assert resolved.config.model == fallback_model_key
