"""Skill 管理器 - 注册、查询、加载 Skill"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models.skill import Skill

logger = logging.getLogger(__name__)


class SkillManager:
    _skill_cache: dict[str, dict] = {}

    @classmethod
    async def register_skill(
        cls,
        db: AsyncSession,
        name: str,
        version: str,
        description: str,
        entry_point: str,
        manifest: dict = None,
        dependencies: list[str] = None,
    ) -> Skill:
        skill = Skill(
            id=f"skill-{name.replace('-', '')}",
            name=name,
            version=version,
            description=description,
            entry_point=entry_point,
            manifest=manifest or {},
            dependencies=dependencies or [],
        )
        db.add(skill)
        await db.commit()
        cls._skill_cache[name] = skill.__dict__.copy()
        return skill

    @classmethod
    async def get_skill(cls, db: AsyncSession, name: str) -> Skill | None:
        if name in cls._skill_cache:
            result = await db.execute(select(Skill).where(Skill.name == name))
            skill = result.scalar_one_or_none()
            if skill:
                cls._skill_cache[name] = skill.__dict__.copy()
            return skill

        result = await db.execute(select(Skill).where(Skill.name == name))
        skill = result.scalar_one_or_none()
        if skill:
            cls._skill_cache[name] = skill.__dict__.copy()
        return skill

    @classmethod
    async def list_skills(cls, db: AsyncSession) -> list[Skill]:
        result = await db.execute(select(Skill))
        skills = result.scalars().all()
        for skill in skills:
            cls._skill_cache[skill.name] = skill.__dict__.copy()
        return skills

    @classmethod
    async def unregister_skill(cls, db: AsyncSession, name: str) -> bool:
        skill = await cls.get_skill(db, name)
        if skill:
            await db.delete(skill)
            await db.commit()
            cls._skill_cache.pop(name, None)
            return True
        return False

    @classmethod
    def load_skill_executor(cls, entry_point: str) -> Any:
        parts = entry_point.split(".")
        module_path = ".".join(parts[:-1])
        function_name = parts[-1]

        try:
            import importlib

            module = importlib.import_module(module_path)
            return getattr(module, function_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load skill executor {entry_point}: {e}")
            return None

    @classmethod
    async def install_from_pypi(cls, db: AsyncSession, package_name: str, version: str = None) -> bool:
        try:
            args = [sys.executable, "-m", "pip", "install"]
            if version:
                args.append(f"{package_name}=={version}")
            else:
                args.append(package_name)

            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to install {package_name}: {result.stderr}")
                return False

            return True
        except Exception as e:
            logger.error(f"Installation error: {e}")
            return False