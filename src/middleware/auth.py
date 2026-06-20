"""权限依赖注入：支持 Bearer Token 和 X-API-Key 双认证"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import decode_token
from agent_forge.config import settings
from agent_forge.database import get_async_session
from agent_forge.models import APIKey, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """双认证：优先 Bearer Token， fallback 到 X-API-Key"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. 尝试 Bearer Token
    if token:
        try:
            payload = decode_token(token)
            user_id: str = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    return user
        except JWTError:
            pass

    # 2. Fallback: X-API-Key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # 简单 hash 比对（生产建议用 hmac）
        import hashlib
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        key_obj = result.scalar_one_or_none()
        if key_obj:
            # 更新 last_used_at
            from datetime import datetime, timezone
            key_obj.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            result = await db.execute(select(User).where(User.id == key_obj.user_id))
            user = result.scalar_one_or_none()
            if user:
                return user

    raise credentials_exception


def require_permission(permission: str):
    """权限校验依赖工厂"""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        perms = current_user.permissions or []
        if permission == "admin" and "admin" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )
        if permission == "read" and "read" not in perms and "admin" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Read permission required",
            )
        return current_user
    return checker
