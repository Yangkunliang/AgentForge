"""认证路由：注册、登录、刷新、退出"""

from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import (  # noqa: E402
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from agent_forge.config import settings  # noqa: E402
from agent_forge.database import get_async_session  # noqa: E402
from agent_forge.models import User  # noqa: E402
from agent_forge.auth.jwt import get_current_user  # noqa: E402

import uuid
import re

router = APIRouter()
logger = logging.getLogger("agent_forge")


# ── Pydantic Schemas ──────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("需含大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("需含小写字母")
        if not re.search(r"\d", v):
            raise ValueError("需含数字")
        return v


class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    permissions: list[str]
    created_at: str

    model_config = {"from_attributes": True}


# ── 路由 ──────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
async def register(body: UserRegisterRequest, db: AsyncSession = Depends(get_async_session)) -> dict:
    """用户注册：bcrypt 密码哈希，默认权限 ["read"]"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="DUPLICATE_USERNAME",
        )

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="DUPLICATE_EMAIL",
        )

    user = User(
        id=str(uuid.uuid4()),
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        permissions=["read"],
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "permissions": user.permissions,
        "created_at": str(user.created_at),
    }


@router.post("/login", tags=["auth"])
async def login(
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """用户登录：验证密码，返回 access_token，写入 refresh_token Cookie"""
    # 通过用户名或邮箱查找用户
    result = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.username))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # 生成 tokens
    access_token = create_access_token({"sub": user.id, "type": "access"})
    refresh_token = create_refresh_token({"sub": user.id, "type": "refresh"})

    response = {
        "access_token": access_token,
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "permissions": user.permissions,
        },
    }

    # 设置 refresh_token Cookie
    from fastapi.responses import JSONResponse

    resp = JSONResponse(content=response)
    resp.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth/refresh",
    )
    return resp


@router.post("/refresh", tags=["auth"])
async def refresh(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """刷新 access_token：从 Cookie 读取 refresh_token"""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="REFRESH_TOKEN_EXPIRED",
        )

    from agent_forge.auth.jwt import decode_token

    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id: str = payload["sub"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="REFRESH_TOKEN_EXPIRED",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token({"sub": user.id, "type": "access"})
    return {"access_token": access_token, "expires_in": settings.access_token_expire_minutes * 60}


@router.post("/logout", tags=["auth"])
async def logout(request: Request) -> dict:
    """退出登录：清除 refresh_token Cookie"""
    from fastapi.responses import JSONResponse

    resp = JSONResponse(content={"detail": "logged_out"})
    resp.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth/refresh",
    )
    return resp
