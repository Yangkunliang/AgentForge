"""LLM 配置路由 — 读/写环境变量中的模型配置"""

from __future__ import annotations

import json
import logging
import os
import re

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from agent_forge.config import settings  # noqa: E402

router = APIRouter()
logger = logging.getLogger("agent_forge")


class LLMConfigOut(BaseModel):
    """只读返回（隐藏真实 API Key）"""
    api_key_set: bool
    default_model: str
    default_temperature: float
    max_tokens: int
    model_routes: dict[str, str]


@router.get("/llm", response_model=LLMConfigOut)
async def get_llm_config() -> dict:
    """返回 LLM 配置（Key 只标记是否设置，不返回明文）"""
    return {
        "api_key_set": bool(settings.api_key),
        "default_model": settings.default_model,
        "default_temperature": settings.default_temperature,
        "max_tokens": settings.max_tokens,
        "model_routes": settings.model_routes_map,
    }


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

# PyPI 包名合法字符
_PACKAGE_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$")


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
        # 不允许 shell 注入字符：分号、&、|、`、$、\n
        if v and re.search(r'[;&|`$]', v):
            raise ValueError("api_key contains invalid characters")
        return v

    @field_validator("model_routes")
    @classmethod
    def validate_model_routes(cls, v: dict[str, str]) -> dict[str, str]:
        """验证 model_routes 的 key/value 不含有 shell 注入字符"""
        sanitized: dict[str, str] = {}
        for k, val in v.items():
            if k and not _MODEL_RE.match(k):
                raise ValueError(f"route key '{k}' contains invalid characters")
            if val and not _MODEL_RE.match(val):
                raise ValueError(f"route value '{val}' contains invalid characters")
            sanitized[k] = val
        return sanitized


@router.post("/llm")
async def update_llm_config(body: LLMConfigIn) -> dict:
    """更新 LLM 配置（写入 .env 文件，重启不丢失）"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")

    # 读取现有 .env
    lines: dict[str, str] = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    lines[key.strip()] = val.strip()

    changes: list[str] = []

    # API Key — 严格校验，防止注入
    if body.api_key is not None:
        env_key = _ALLOWED_ENV_KEYS["api_key"]
        lines[env_key] = body.api_key
        changes.append("api_key")
        os.environ[env_key] = body.api_key

    # 默认模型 — 已做 field_validator 校验
    env_key = _ALLOWED_ENV_KEYS["default_model"]
    lines[env_key] = body.default_model
    changes.append("default_model")
    os.environ[env_key] = body.default_model

    # 多模态模型 — 已做 field_validator 校验
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

    # Model Routes — JSON 安全写入，已在 validator 中过滤
    env_key = _ALLOWED_ENV_KEYS["model_routes"]
    lines[env_key] = json.dumps(body.model_routes) if body.model_routes else ""
    changes.append("model_routes")
    os.environ[env_key] = lines[env_key]

    # 写回 .env（只写白名单键，不触碰其他行）
    with open(env_path, "w") as f:
        for k, v in lines.items():
            f.write(f"{k}={v}\n")

    return {"ok": True, "changed": changes, "message": "配置已更新，部分设置需要重启服务后生效"}
