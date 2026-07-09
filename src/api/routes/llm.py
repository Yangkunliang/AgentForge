"""LLM settings routes."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_forge.config import settings
from agent_forge.database import get_async_session
from agent_forge.models import LLMCredential, LLMModelSetting, LLMProviderSetting, LLMRoute, User
from agent_forge.security.credentials import encrypt_secret
from middleware.auth import require_permission

router = APIRouter()


class LLMProviderResponse(BaseModel):
    id: str
    provider_key: str
    name: str
    base_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class LLMModelResponse(BaseModel):
    id: str
    provider_id: str
    provider_key: str | None = None
    model_key: str
    name: str
    capabilities: list[str]
    context_window: int | None
    input_price_per_1m: float | None
    output_price_per_1m: float | None
    status: str
    created_at: datetime
    updated_at: datetime


class LLMCredentialResponse(BaseModel):
    id: str
    provider_id: str
    provider_key: str | None = None
    name: str
    secret_set: bool
    masked_secret: str
    active: bool
    created_at: datetime
    updated_at: datetime


class LLMRouteResponse(BaseModel):
    id: str
    route_key: str
    name: str
    provider_id: str
    provider_key: str | None
    model_id: str
    model_name: str | None
    credential_id: str | None
    credential_name: str | None
    temperature: float
    max_tokens: int
    timeout_seconds: int
    fallback_route_keys: list[str]
    active: bool
    created_at: datetime
    updated_at: datetime


class LLMConfigOut(BaseModel):
    """Read-only legacy config plus structured route snapshot."""

    api_key_set: bool
    default_model: str
    default_temperature: float
    max_tokens: int
    model_routes: dict[str, str]
    providers: list[LLMProviderResponse] = Field(default_factory=list)
    models: list[LLMModelResponse] = Field(default_factory=list)
    credentials: list[LLMCredentialResponse] = Field(default_factory=list)
    routes: list[LLMRouteResponse] = Field(default_factory=list)


# 允许写入的 .env 键名白名单（与 LLMConfigIn 字段一一映射）
_ALLOWED_ENV_KEYS: dict[str, str] = {
    "api_key": "LLM_API_KEY",
    "default_model": "LLM_MODEL",
    "vision_model": "VL_MODEL",
    "image_gen_model": "T2I_MODEL",
    "model_routes": "MODEL_ROUTES",
}

# 模型名/URL 合法字符：字母、数字、正斜杠、短横线、下划线、点、星号（如 openai/gpt-4o-mini）
_MODEL_RE = re.compile(r"^[a-zA-Z0-9/_\*.:-]+$")
_KEY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9/_\*.:-]{0,159}$")


class LLMConfigIn(BaseModel):
    default_model: str
    default_temperature: float
    max_tokens: int
    model_routes: dict[str, str] = {}
    api_key: str | None = None
    vision_model: str = ""
    image_gen_model: str = ""

    @field_validator("default_model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if v and not _MODEL_RE.match(v):
            raise ValueError("model name must contain only letters, digits, /, -, _, ., *, :")
        return v

    @field_validator("vision_model")
    @classmethod
    def validate_vision_model(cls, v: str) -> str:
        if v and not _MODEL_RE.match(v):
            raise ValueError("vision model name is invalid")
        return v

    @field_validator("image_gen_model")
    @classmethod
    def validate_image_gen_model(cls, v: str) -> str:
        if v and not _MODEL_RE.match(v):
            raise ValueError("image gen model name is invalid")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 4096:
            raise ValueError("api_key is too long (max 4096 chars)")
        if v and re.search(r'[;&|`$]', v):
            raise ValueError("api_key contains invalid characters")
        return v

    @field_validator("model_routes")
    @classmethod
    def validate_model_routes(cls, v: dict[str, str]) -> dict[str, str]:
        sanitized: dict[str, str] = {}
        for k, val in v.items():
            if k and not _MODEL_RE.match(k):
                raise ValueError(f"route key '{k}' contains invalid characters")
            if val and not _MODEL_RE.match(val):
                raise ValueError(f"route value '{val}' contains invalid characters")
            sanitized[k] = val
        return sanitized


class LLMProviderCreate(BaseModel):
    provider_key: str = Field(..., min_length=1, max_length=60)
    name: str = Field(..., min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=500)
    status: str = Field(default="active", pattern="^(active|inactive)$")

    @field_validator("provider_key")
    @classmethod
    def validate_provider_key(cls, value: str) -> str:
        if not _KEY_RE.match(value):
            raise ValueError("provider_key is invalid")
        return value


class LLMModelCreate(BaseModel):
    provider_id: str
    model_key: str = Field(..., min_length=1, max_length=160)
    name: str = Field(..., min_length=1, max_length=160)
    capabilities: list[str] = Field(default_factory=list)
    context_window: int | None = Field(default=None, ge=1)
    input_price_per_1m: float | None = Field(default=None, ge=0)
    output_price_per_1m: float | None = Field(default=None, ge=0)
    status: str = Field(default="active", pattern="^(active|inactive)$")

    @field_validator("model_key")
    @classmethod
    def validate_model_key(cls, value: str) -> str:
        if not _MODEL_RE.match(value):
            raise ValueError("model_key is invalid")
        return value


class LLMCredentialCreate(BaseModel):
    provider_id: str
    name: str = Field(..., min_length=1, max_length=120)
    secret: str = Field(..., min_length=1, max_length=4096)
    active: bool = True

    @field_validator("secret")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if re.search(r'[;&|`$]', value):
            raise ValueError("secret contains invalid characters")
        return value


class LLMRouteCreate(BaseModel):
    route_key: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=120)
    provider_id: str
    model_id: str
    credential_id: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    fallback_route_keys: list[str] = Field(default_factory=list)
    active: bool = True

    @field_validator("route_key")
    @classmethod
    def validate_route_key(cls, value: str) -> str:
        if not _KEY_RE.match(value):
            raise ValueError("route_key is invalid")
        return value


class LLMRouteListResponse(BaseModel):
    items: list[LLMRouteResponse]


@router.get("/llm", response_model=LLMConfigOut)
async def get_llm_config(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("read")),
) -> dict:
    """返回 LLM 配置（Key 只标记是否设置，不返回明文）。"""
    providers, models, credentials, routes = await _snapshot(db, current_user.id)
    return {
        "api_key_set": bool(settings.api_key),
        "default_model": settings.default_model,
        "default_temperature": settings.default_temperature,
        "max_tokens": settings.max_tokens,
        "model_routes": settings.model_routes_map,
        "providers": providers,
        "models": models,
        "credentials": credentials,
        "routes": routes,
    }


@router.post("/llm")
async def update_llm_config(
    body: LLMConfigIn,
    current_user: User = Depends(require_permission("admin")),
) -> dict:
    """更新旧版 LLM 配置（写入 .env 文件，重启不丢失）。"""
    _ = current_user
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")

    lines: dict[str, str] = {}
    if os.path.exists(env_path):
        with open(env_path) as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    lines[key.strip()] = val.strip()

    changes: list[str] = []

    if body.api_key is not None:
        env_key = _ALLOWED_ENV_KEYS["api_key"]
        lines[env_key] = body.api_key
        changes.append("api_key")
        os.environ[env_key] = body.api_key

    env_key = _ALLOWED_ENV_KEYS["default_model"]
    lines[env_key] = body.default_model
    changes.append("default_model")
    os.environ[env_key] = body.default_model

    if body.vision_model:
        env_key = _ALLOWED_ENV_KEYS["vision_model"]
        lines[env_key] = body.vision_model
        changes.append("vision_model")
        os.environ[env_key] = body.vision_model
    if body.image_gen_model:
        env_key = _ALLOWED_ENV_KEYS["image_gen_model"]
        lines[env_key] = body.image_gen_model
        changes.append("image_gen_model")
        os.environ[env_key] = body.image_gen_model

    env_key = _ALLOWED_ENV_KEYS["model_routes"]
    lines[env_key] = json.dumps(body.model_routes) if body.model_routes else ""
    changes.append("model_routes")
    os.environ[env_key] = lines[env_key]

    with open(env_path, "w") as file:
        for key, value in lines.items():
            file.write(f"{key}={value}\n")

    return {"ok": True, "changed": changes, "message": "配置已更新，部分设置需要重启服务后生效"}


@router.get("/llm/providers", response_model=list[LLMProviderResponse])
async def list_llm_providers(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("read")),
) -> list[dict]:
    result = await db.execute(
        select(LLMProviderSetting).where(LLMProviderSetting.user_id == current_user.id)
    )
    return [_provider_to_dict(provider) for provider in result.scalars().all()]


@router.post("/llm/providers", response_model=LLMProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_provider(
    body: LLMProviderCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("admin")),
) -> dict:
    existing = await db.execute(
        select(LLMProviderSetting).where(
            LLMProviderSetting.user_id == current_user.id,
            LLMProviderSetting.provider_key == body.provider_key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Provider key already exists")

    provider = LLMProviderSetting(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        provider_key=body.provider_key,
        name=body.name,
        base_url=body.base_url,
        status=body.status,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return _provider_to_dict(provider)


@router.get("/llm/models", response_model=list[LLMModelResponse])
async def list_llm_models(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("read")),
) -> list[dict]:
    result = await db.execute(
        select(LLMModelSetting)
        .where(LLMModelSetting.user_id == current_user.id)
        .options(selectinload(LLMModelSetting.provider))
    )
    return [_model_to_dict(model) for model in result.scalars().all()]


@router.post("/llm/models", response_model=LLMModelResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_model(
    body: LLMModelCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("admin")),
) -> dict:
    provider = await _owned_provider_or_404(db, body.provider_id, current_user.id)
    existing = await db.execute(
        select(LLMModelSetting).where(
            LLMModelSetting.user_id == current_user.id,
            LLMModelSetting.model_key == body.model_key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Model key already exists")

    model = LLMModelSetting(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        provider_id=provider.id,
        model_key=body.model_key,
        name=body.name,
        capabilities=body.capabilities,
        context_window=body.context_window,
        input_price_per_1m=body.input_price_per_1m,
        output_price_per_1m=body.output_price_per_1m,
        status=body.status,
    )
    model.provider = provider
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return _model_to_dict(model)


@router.get("/llm/credentials", response_model=list[LLMCredentialResponse])
async def list_llm_credentials(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("read")),
) -> list[dict]:
    result = await db.execute(
        select(LLMCredential)
        .where(LLMCredential.user_id == current_user.id)
        .options(selectinload(LLMCredential.provider))
    )
    return [_credential_to_dict(credential) for credential in result.scalars().all()]


@router.post("/llm/credentials", response_model=LLMCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_credential(
    body: LLMCredentialCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("admin")),
) -> dict:
    provider = await _owned_provider_or_404(db, body.provider_id, current_user.id)
    credential = LLMCredential(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        provider_id=provider.id,
        name=body.name,
        encrypted_secret=encrypt_secret(body.secret),
        secret_hint=_mask_secret(body.secret),
        active=body.active,
    )
    credential.provider = provider
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return _credential_to_dict(credential)


@router.get("/llm/routes", response_model=LLMRouteListResponse)
async def list_llm_routes(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("read")),
) -> dict:
    routes = await _load_routes(db, current_user.id)
    return {"items": [_route_to_dict(route) for route in routes]}


@router.post("/llm/routes", response_model=LLMRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_route(
    body: LLMRouteCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("admin")),
) -> dict:
    provider = await _owned_provider_or_404(db, body.provider_id, current_user.id)
    model = await _owned_model_or_404(db, body.model_id, current_user.id)
    if model.provider_id != provider.id:
        raise HTTPException(status_code=400, detail="Model does not belong to provider")

    credential: LLMCredential | None = None
    if body.credential_id:
        credential = await _owned_credential_or_404(db, body.credential_id, current_user.id)
        if credential.provider_id != provider.id:
            raise HTTPException(status_code=400, detail="Credential does not belong to provider")

    existing = await db.execute(
        select(LLMRoute).where(LLMRoute.user_id == current_user.id, LLMRoute.route_key == body.route_key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Route key already exists")

    route = LLMRoute(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        route_key=body.route_key,
        name=body.name,
        provider_id=provider.id,
        model_id=model.id,
        credential_id=credential.id if credential else None,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        timeout_seconds=body.timeout_seconds,
        fallback_route_keys=body.fallback_route_keys,
        active=body.active,
    )
    route.provider = provider
    route.model = model
    route.credential = credential
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return _route_to_dict(route)


async def _snapshot(db: AsyncSession, user_id: str) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    provider_result = await db.execute(
        select(LLMProviderSetting).where(LLMProviderSetting.user_id == user_id)
    )
    model_result = await db.execute(
        select(LLMModelSetting)
        .where(LLMModelSetting.user_id == user_id)
        .options(selectinload(LLMModelSetting.provider))
    )
    credential_result = await db.execute(
        select(LLMCredential)
        .where(LLMCredential.user_id == user_id)
        .options(selectinload(LLMCredential.provider))
    )
    routes = await _load_routes(db, user_id)
    return (
        [_provider_to_dict(provider) for provider in provider_result.scalars().all()],
        [_model_to_dict(model) for model in model_result.scalars().all()],
        [_credential_to_dict(credential) for credential in credential_result.scalars().all()],
        [_route_to_dict(route) for route in routes],
    )


async def _load_routes(db: AsyncSession, user_id: str) -> list[LLMRoute]:
    result = await db.execute(
        select(LLMRoute)
        .where(LLMRoute.user_id == user_id)
        .options(
            selectinload(LLMRoute.provider),
            selectinload(LLMRoute.model),
            selectinload(LLMRoute.credential),
        )
    )
    return list(result.scalars().all())


async def _owned_provider_or_404(db: AsyncSession, provider_id: str, user_id: str) -> LLMProviderSetting:
    result = await db.execute(
        select(LLMProviderSetting).where(
            LLMProviderSetting.id == provider_id,
            LLMProviderSetting.user_id == user_id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


async def _owned_model_or_404(db: AsyncSession, model_id: str, user_id: str) -> LLMModelSetting:
    result = await db.execute(
        select(LLMModelSetting).where(LLMModelSetting.id == model_id, LLMModelSetting.user_id == user_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


async def _owned_credential_or_404(db: AsyncSession, credential_id: str, user_id: str) -> LLMCredential:
    result = await db.execute(
        select(LLMCredential).where(LLMCredential.id == credential_id, LLMCredential.user_id == user_id)
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential


def _provider_to_dict(provider: LLMProviderSetting) -> dict:
    return {
        "id": provider.id,
        "provider_key": provider.provider_key,
        "name": provider.name,
        "base_url": provider.base_url,
        "status": provider.status,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at,
    }


def _model_to_dict(model: LLMModelSetting) -> dict:
    return {
        "id": model.id,
        "provider_id": model.provider_id,
        "provider_key": model.provider.provider_key if model.provider else None,
        "model_key": model.model_key,
        "name": model.name,
        "capabilities": model.capabilities or [],
        "context_window": model.context_window,
        "input_price_per_1m": model.input_price_per_1m,
        "output_price_per_1m": model.output_price_per_1m,
        "status": model.status,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _credential_to_dict(credential: LLMCredential) -> dict:
    return {
        "id": credential.id,
        "provider_id": credential.provider_id,
        "provider_key": credential.provider.provider_key if credential.provider else None,
        "name": credential.name,
        "secret_set": True,
        "masked_secret": credential.secret_hint,
        "active": credential.active,
        "created_at": credential.created_at,
        "updated_at": credential.updated_at,
    }


def _route_to_dict(route: LLMRoute) -> dict:
    return {
        "id": route.id,
        "route_key": route.route_key,
        "name": route.name,
        "provider_id": route.provider_id,
        "provider_key": route.provider.provider_key if route.provider else None,
        "model_id": route.model_id,
        "model_name": route.model.model_key if route.model else None,
        "credential_id": route.credential_id,
        "credential_name": route.credential.name if route.credential else None,
        "temperature": route.temperature,
        "max_tokens": route.max_tokens,
        "timeout_seconds": route.timeout_seconds,
        "fallback_route_keys": route.fallback_route_keys or [],
        "active": route.active,
        "created_at": route.created_at,
        "updated_at": route.updated_at,
    }


def _mask_secret(secret: str) -> str:
    if len(secret) <= 8:
        return "****"
    return f"{secret[:4]}...{secret[-4:]}"
