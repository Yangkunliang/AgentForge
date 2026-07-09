"""Skill 管理器 - 注册、查询、加载 Skill"""

from __future__ import annotations

import logging
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
        entry_point: str | None = None,
        manifest: dict | None = None,
        manifest_hash: str | None = None,
        permissions: list[str] | None = None,
        runtime_spec: dict | None = None,
        audit_level: str = "standard",
        dependencies: list[str] | None = None,
        source_type: str = "builtin",
        github_url: str | None = None,
        tags: list[str] | None = None,
        icon_url: str | None = None,
    ) -> Skill:
        """注册或更新 Skill。若同名 Skill 已存在则更新版本信息。"""
        # 检查是否已存在
        existing = await cls.get_skill(db, name)
        if existing:
            # 更新版本/描述（幂等注册）
            existing.version = version
            existing.description = description
            if entry_point:
                existing.entry_point = entry_point
            if manifest:
                existing.manifest = manifest
            if manifest_hash is not None:
                existing.manifest_hash = manifest_hash
            if permissions is not None:
                existing.permissions = permissions
            if runtime_spec is not None:
                existing.runtime_spec = runtime_spec
            existing.audit_level = audit_level
            existing.source_type = source_type
            if github_url is not None:
                existing.github_url = github_url
            if tags is not None:
                existing.tags = tags
            if icon_url is not None:
                existing.icon_url = icon_url
            await db.commit()
            cls._skill_cache[name] = existing.__dict__.copy()
            return existing

        import uuid
        skill = Skill(
            id=f"skill-{uuid.uuid4().hex[:8]}",
            name=name,
            version=version,
            description=description,
            entry_point=entry_point,
            manifest=manifest or {},
            manifest_hash=manifest_hash,
            permissions=permissions or [],
            runtime_spec=runtime_spec or {},
            audit_level=audit_level,
            dependencies=dependencies or [],
            source_type=source_type,
            github_url=github_url,
            tags=tags or [],
            icon_url=icon_url,
            enabled=True,
        )
        db.add(skill)
        await db.commit()
        cls._skill_cache[name] = skill.__dict__.copy()
        return skill

    @classmethod
    async def get_skill(cls, db: AsyncSession, name: str) -> Skill | None:
        result = await db.execute(select(Skill).where(Skill.name == name))
        skill = result.scalar_one_or_none()
        if skill:
            cls._skill_cache[name] = skill.__dict__.copy()
        return skill

    @classmethod
    async def list_skills(cls, db: AsyncSession, enabled_only: bool = False) -> list[Skill]:
        query = select(Skill)
        if enabled_only:
            query = query.where(Skill.enabled == True)  # noqa: E712
        result = await db.execute(query)
        skills = list(result.scalars().all())
        for skill in skills:
            cls._skill_cache[skill.name] = skill.__dict__.copy()
        return skills

    @classmethod
    async def set_enabled(cls, db: AsyncSession, name: str, enabled: bool) -> bool:
        skill = await cls.get_skill(db, name)
        if not skill:
            return False
        skill.enabled = enabled
        await db.commit()
        cls._skill_cache.pop(name, None)

        # 同步更新 Registry
        from agent_forge.skills.registry import get_skill_registry
        registry = get_skill_registry()
        if not enabled:
            registry.unregister(name)
        return True

    @classmethod
    async def unregister_skill(cls, db: AsyncSession, name: str) -> bool:
        skill = await cls.get_skill(db, name)
        if skill:
            await db.delete(skill)
            await db.commit()
            cls._skill_cache.pop(name, None)
            # 从 Registry 中移除
            from agent_forge.skills.registry import get_skill_registry
            get_skill_registry().unregister(name)
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
            logger.error("Failed to load skill executor %s: %s", entry_point, e)
            return None

    @classmethod
    async def install_from_pypi(cls, db: AsyncSession, package_name: str, version: str | None = None) -> bool:
        import subprocess
        try:
            args = [sys.executable, "-m", "pip", "install"]
            if version:
                args.append(f"{package_name}=={version}")
            else:
                args.append(package_name)
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("Failed to install %s: %s", package_name, result.stderr)
                return False
            return True
        except Exception as e:
            logger.error("Installation error: %s", e)
            return False
