"""Update Profile Skill — 更新用户个人资料

让 Agent 帮助用户更新个人资料（昵称、头像），无需用户手动访问设置页面。

适用场景：
  - 用户说"帮我设置昵称"
  - 用户说"修改我的头像"
  - 用户希望更新个人信息
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import async_session_factory
from agent_forge.models import User

logger = logging.getLogger(__name__)

UPDATE_PROFILE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "update_profile",
        "description": (
            "更新当前用户的个人资料（昵称、头像）。"
            "当用户请求修改个人信息（如设置昵称、更换头像）时调用。"
            "此工具会自动使用当前登录用户的身份进行更新。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nickname": {
                    "type": "string",
                    "description": "新的昵称，长度不超过 50 个字符",
                },
                "avatar_url": {
                    "type": "string",
                    "description": "头像图片的 data URL（base64 编码），如 data:image/png;base64,xxx...",
                },
            },
            "required": [],
        },
    },
}


async def update_profile(user_id: str, nickname: str | None = None, avatar_url: str | None = None) -> dict[str, Any]:
    """
    更新用户个人资料

    Args:
        user_id: 当前登录用户的 ID（从请求上下文获取）
        nickname: 新昵称，可选
        avatar_url: 头像 data URL，可选

    Returns:
        更新结果
    """
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "reason": "用户不存在",
            }

        if nickname is not None:
            nickname = nickname.strip()
            if len(nickname) > 50:
                return {
                    "success": False,
                    "reason": "昵称长度不能超过 50 个字符",
                }
            user.nickname = nickname or None

        if avatar_url is not None:
            if avatar_url == "":
                user.avatar_url = None
            elif avatar_url.startswith("data:image/"):
                if len(avatar_url) > 700_000:
                    return {
                        "success": False,
                        "reason": "头像文件过大，请压缩后重试",
                    }
                user.avatar_url = avatar_url
            else:
                return {
                    "success": False,
                    "reason": "头像必须为 data URL 格式",
                }

        await db.commit()

        logger.info("User %s updated profile: nickname=%s", user.username, nickname)

        return {
            "success": True,
            "message": "个人资料更新成功",
            "data": {
                "nickname": user.nickname,
                "avatar_url": user.avatar_url,
            },
        }