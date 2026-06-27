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
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter for auth routes (stricter limits to prevent brute-force)
_auth_limiter = Limiter(key_func=get_remote_address, default_limits=[])
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
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
@_auth_limiter.limit("5/minute")
async def register(request: Request, body: UserRegisterRequest, db: AsyncSession = Depends(get_async_session)) -> dict:
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
        "access_token": create_access_token({"sub": user.id, "type": "access"}),
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "permissions": user.permissions,
            "created_at": str(user.created_at),
        },
    }


@router.post("/login", tags=["auth"])
@_auth_limiter.limit("10/minute")
async def login(request: Request, body: UserLoginRequest, db: AsyncSession = Depends(get_async_session)) -> dict:
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
            "email": user.email,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
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
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",
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
        path="/api/v1/auth",
    )
    return resp


@router.get("/me", tags=["auth"])
async def me(current_user: User = Depends(get_current_user)) -> dict:
    """返回当前登录用户信息"""
    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
            "permissions": current_user.permissions,
            "created_at": str(current_user.created_at),
        }
    }


class UpdateProfileRequest(BaseModel):
    nickname: str | None = Field(None, max_length=50)
    avatar_url: str | None = Field(None)  # base64 data URL
    current_password: str | None = Field(None)  # 修改密码时需提供
    new_password: str | None = Field(None, min_length=8, max_length=128)

    @field_validator("nickname")
    @classmethod
    def clean_nickname(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.search(r"[A-Z]", v):
            raise ValueError("需含大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("需含小写字母")
        if not re.search(r"\d", v):
            raise ValueError("需含数字")
        return v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # 必须是 data URL 或空字符串（清除头像）
        if v == "":
            return None
        if not v.startswith("data:image/"):
            raise ValueError("头像必须为 data URL 格式")
        # base64 大小检查：约 512 KB
        if len(v) > 700_000:
            raise ValueError("头像文件过大，请压缩后重试")
        return v


@router.patch("/me", tags=["auth"])
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """更新个人资料：昵称、头像、密码"""
    # 修改密码需验证原密码
    if body.new_password:
        if not body.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CURRENT_PASSWORD_REQUIRED",
            )
        if not verify_password(body.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="WRONG_CURRENT_PASSWORD",
            )
        current_user.password_hash = hash_password(body.new_password)

    if body.nickname is not None:
        current_user.nickname = body.nickname or None

    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url or None

    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)

    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
            "permissions": current_user.permissions,
            "created_at": str(current_user.created_at),
        }
    }
