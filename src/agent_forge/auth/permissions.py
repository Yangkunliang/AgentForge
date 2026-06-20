"""权限依赖 - 检查用户权限"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from agent_forge.auth.jwt import get_current_active_user
from agent_forge.models.user import User


async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if "admin" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required",
        )
    return current_user