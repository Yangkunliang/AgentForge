"""Skill API 路由"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.permissions import get_admin_user
from agent_forge.database import get_async_session
from agent_forge.models.skill import Skill
from agent_forge.models.user import User
from agent_forge.skills.installer import SkillInstaller
from agent_forge.skills.manager import SkillManager

router = APIRouter(prefix="/skills", tags=["skills"])


class InstallSkillRequest(BaseModel):
    source: str
    version: str | None = None


class SkillManifestResponse(BaseModel):
    name: str
    version: str
    description: str
    entry_point: str
    installed_at: str | None

    @classmethod
    def from_model(cls, skill: Skill) -> "SkillManifestResponse":
        return cls(
            name=skill.name,
            version=skill.version,
            description=skill.description,
            entry_point=skill.entry_point,
            installed_at=skill.installed_at,
        )


@router.post("/install", status_code=status.HTTP_202_ACCEPTED)
async def install_skill(
    request: InstallSkillRequest,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_admin_user),
):
    install_task = await SkillInstaller.start_install(db, request.source, request.version)
    return {
        "install_id": install_task.id,
        "skill_name": install_task.skill_name,
        "status": install_task.status,
    }


@router.get("/install/{install_id}")
async def get_install_status(
    install_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_admin_user),
):
    install_task = await SkillInstaller.get_install_status(db, install_id)
    if not install_task:
        raise HTTPException(status_code=404, detail="Install task not found")
    return {
        "install_id": install_task.id,
        "skill_name": install_task.skill_name,
        "status": install_task.status,
        "log": install_task.log,
        "error": install_task.error,
    }


@router.get("")
async def list_skills(
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_admin_user),
):
    skills = await SkillManager.list_skills(db)
    return {
        "total": len(skills),
        "items": [SkillManifestResponse.from_model(s) for s in skills],
    }


@router.delete("/{skill_name}", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_skill(
    skill_name: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_admin_user),
):
    success = await SkillManager.unregister_skill(db, skill_name)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    await SkillInstaller.uninstall_skill(db, skill_name)