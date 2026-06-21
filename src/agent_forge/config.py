"""应用配置"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


def _find_env() -> Path:
    # 开发环境自动加载 .env
    return Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agentforge"
    postgres_user: str = "agent"
    postgres_password: str = "agent"
    postgres_db: str = "agentforge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_management_url: str = "http://localhost:15672"

    # JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Rate limiting
    rate_limit_default: str = "100/minute"

    # LLM
    llm_base_url: str = Field(default="", validation_alias="LLM_BASE_URL")
    api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    default_model: str = Field(default="openai/gpt-4o-mini", validation_alias="LLM_MODEL")
    default_temperature: float = 0.7
    max_tokens: int = 4096
    # 多模型路由: vision / image_gen 自动纳入
    vision_model: str = Field(default="", validation_alias="VL_MODEL")
    image_gen_model: str = Field(default="", validation_alias="T2I_MODEL")
    model_routes: str = Field(default="{}", validation_alias="MODEL_ROUTES")  # JSON: {"claude": "anthropic/claude-3-5-sonnet", ...}

    @property
    def model_routes_map(self) -> dict[str, str]:
        """合并用户自定义 routes + 多模态模型为自动 route"""
        routes: dict[str, str] = {}
        if self.model_routes:
            try:
                routes = json.loads(self.model_routes)
            except json.JSONDecodeError:
                pass
        if self.vision_model:
            routes["vision"] = self.vision_model
        if self.image_gen_model:
            routes["image_gen"] = self.image_gen_model
        return routes

    # Logging
    log_level: str = "INFO"

    @property
    def cors_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {
        "env_file": str(_find_env()),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
