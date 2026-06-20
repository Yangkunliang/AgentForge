"""Alembic 配置"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 将 src/ 添加到 path 以便 import models
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from agent_forge.config import settings  # noqa: E402
from agent_forge.models import *  # noqa: E402, F401, F403
from agent_forge.models.base import Base  # noqa: E402

# Alembic 使用 sync engine（将 asyncpg URL 转为 psycopg2 URL）
config = context.config
sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_db_url)

# 绑定 metadata 用于 alembic revision --autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """以只读模式运行迁移（用于生成 SQL 或离线迁移）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在在线模式下运行迁移（使用真实数据库）"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
