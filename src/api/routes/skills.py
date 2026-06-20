"""Skill 管理路由：列表、安装、卸载"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import get_async_session
from agent_forge.models import User
from agent_forge.skills.installer import SkillInstaller
from agent_forge.skills.manager import SkillManager
from middleware.auth import get_current_user, require_permission

router = APIRouter()
logger = logging.getLogger("agent_forge")


# ── 请求/响应 Schema ──────────────────────────────────────────

class InstallSkillRequest(BaseModel):
    source: str
    version: str | None = None


class SkillManifest(BaseModel):
    name: str
    version: str
    description: str
    entry_point: str
    installed_at: str | None


class InstallStatusResponse(BaseModel):
    install_id: str
    status: str
    log: str | None = None
    error: str | None = None


class InstallTaskCreated(BaseModel):
    install_id: str
    skill_name: str
    status: str


# ── 端点 ──────────────────────────────────────────────────────

@router.get("")
async def list_skills(
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_user),
) -> dict:
    skills = await SkillManager.list_skills(db)
    items = [
        SkillManifest(
            name=s.name,
            version=s.version,
            description=s.description,
            entry_point=s.entry_point,
            installed_at=s.installed_at,
        ).model_dump()
        for s in skills
    ]
    return {"total": len(items), "items": items}


@router.get("/install/{install_id}")
async def get_install_status(
    install_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_user),
) -> dict:
    task = await SkillInstaller.get_install_status(db, install_id)
    if not task:
        raise HTTPException(status_code=404, detail="Install task not found")
    return InstallStatusResponse(
        install_id=task.id,
        status=task.status,
        log=task.log,
        error=task.error,
    ).model_dump()


@router.post("/install", status_code=status.HTTP_202_ACCEPTED)
async def install_skill(
    body: InstallSkillRequest,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(require_permission("admin")),
) -> dict:
    install_task = await SkillInstaller.start_install(db, body.source, body.version)
    return InstallTaskCreated(
        install_id=install_task.id,
        skill_name=install_task.skill_name,
        status=install_task.status,
    ).model_dump()


@router.delete("/{skill_name}", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_skill(
    skill_name: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(require_permission("admin")),
) -> None:
    success = await SkillManager.unregister_skill(db, skill_name)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    await SkillInstaller.uninstall_skill(db, skill_name)
