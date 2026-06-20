"""Rate limiting 中间件（slowapi + Redis）"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from agent_forge.config import settings  # noqa: E402

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    storage_uri=settings.redis_url,
)
