"""LLM 配置路由 — 读/写环境变量中的模型配置"""

from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter
from pydantic import BaseModel

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


class LLMConfigIn(BaseModel):
    default_model: str
    default_temperature: float
    max_tokens: int
    model_routes: dict[str, str] = {}
    api_key: str | None = None
    vision_model: str = ""
    image_gen_model: str = ""


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

    # API Key
    if body.api_key is not None:
        lines["API_KEY"] = body.api_key
        changes.append("api_key")
        os.environ["API_KEY"] = body.api_key

    # 默认模型
    lines["DEFAULT_MODEL"] = body.default_model
    changes.append("default_model")
    os.environ["DEFAULT_MODEL"] = body.default_model

    # 多模态模型
    if body.vision_model:
        lines["VISION_MODEL"] = body.vision_model
        changes.append("vision_model")
        os.environ["VISION_MODEL"] = body.vision_model
    if body.image_gen_model:
        lines["IMAGE_GEN_MODEL"] = body.image_gen_model
        changes.append("image_gen_model")
        os.environ["IMAGE_GEN_MODEL"] = body.image_gen_model

    # Model Routes
    lines["MODEL_ROUTES"] = json.dumps(body.model_routes) if body.model_routes else ""
    changes.append("model_routes")
    os.environ["MODEL_ROUTES"] = lines["MODEL_ROUTES"]

    # 写回 .env
    with open(env_path, "w") as f:
        for k, v in lines.items():
            f.write(f"{k}={v}\n")

    return {"ok": True, "changed": changes, "message": "配置已更新，部分设置需要重启服务后生效"}
