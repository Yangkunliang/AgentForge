"""Model route resolver for stage runtime execution."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_forge.config import settings
from agent_forge.llm.provider import LLMConfig
from agent_forge.models import LLMRoute
from agent_forge.security.credentials import decrypt_secret


@dataclass(frozen=True)
class ModelRouteResolution:
    route_key: str
    name: str
    source: str
    provider_key: str
    model_name: str
    config: LLMConfig
    credential_id: str | None = None
    credential_name: str | None = None
    fallback_route_keys: list[str] | None = None
    requested_route_key: str | None = None

    def to_context(self) -> dict:
        return {
            "route_key": self.route_key,
            "name": self.name,
            "source": self.source,
            "provider_key": self.provider_key,
            "model_name": self.model_name,
            "credential_id": self.credential_id,
            "credential_name": self.credential_name,
            "fallback_route_keys": self.fallback_route_keys or [],
            "requested_route_key": self.requested_route_key or self.route_key,
        }


class ModelRouteUnavailable(Exception):
    """Raised when a configured model route cannot be used."""


async def resolve_model_route(
    db: AsyncSession,
    *,
    user_id: str,
    requested_key: str | None = None,
    fallback_model_name: str | None = None,
) -> ModelRouteResolution:
    """Resolve a user-scoped model route and fall back to legacy settings."""
    route_key = requested_key or "default"
    route = await _get_route(db, user_id=user_id, route_key=route_key)
    if route:
        if _is_available(route):
            return _route_resolution(route, requested_route_key=route_key, source="database")

        for fallback_key in route.fallback_route_keys or []:
            fallback_route = await _get_route(db, user_id=user_id, route_key=fallback_key)
            if fallback_route and _is_available(fallback_route):
                return _route_resolution(fallback_route, requested_route_key=route_key, source="fallback")

    return _legacy_resolution(route_key, fallback_model_name=fallback_model_name)


async def _get_route(db: AsyncSession, *, user_id: str, route_key: str) -> LLMRoute | None:
    result = await db.execute(
        select(LLMRoute)
        .where(LLMRoute.user_id == user_id, LLMRoute.route_key == route_key)
        .options(
            selectinload(LLMRoute.provider),
            selectinload(LLMRoute.model),
            selectinload(LLMRoute.credential),
        )
    )
    return result.scalar_one_or_none()


def _is_available(route: LLMRoute) -> bool:
    credential_available = route.credential is None or route.credential.active
    return (
        route.active
        and route.provider.status == "active"
        and route.model.status == "active"
        and credential_available
    )


def _route_resolution(
    route: LLMRoute,
    *,
    requested_route_key: str,
    source: str,
) -> ModelRouteResolution:
    credential = route.credential
    api_key = decrypt_secret(credential.encrypted_secret) if credential else None
    return ModelRouteResolution(
        route_key=route.route_key,
        name=route.name,
        source=source,
        provider_key=route.provider.provider_key,
        model_name=route.model.model_key,
        credential_id=credential.id if credential else None,
        credential_name=credential.name if credential else None,
        fallback_route_keys=list(route.fallback_route_keys or []),
        requested_route_key=requested_route_key,
        config=LLMConfig(
            model=route.model.model_key,
            temperature=route.temperature,
            max_tokens=route.max_tokens,
            timeout=route.timeout_seconds,
            api_key=api_key,
            api_base=route.provider.base_url,
            provider_key=route.provider.provider_key,
        ),
    )


def _legacy_resolution(route_key: str, *, fallback_model_name: str | None) -> ModelRouteResolution:
    routes = settings.model_routes_map
    model_name = routes.get(route_key) or fallback_model_name or settings.default_model
    provider_key = model_name.split("/", 1)[0] if "/" in model_name else "default"
    return ModelRouteResolution(
        route_key=route_key,
        name="Legacy Settings",
        source="legacy_settings",
        provider_key=provider_key,
        model_name=model_name,
        credential_id=None,
        credential_name=None,
        fallback_route_keys=[],
        requested_route_key=route_key,
        config=LLMConfig(
            model=model_name,
            temperature=settings.default_temperature,
            max_tokens=settings.max_tokens,
            timeout=60,
            api_key=settings.api_key or None,
            api_base=settings.llm_base_url or None,
            provider_key=provider_key,
        ),
    )
