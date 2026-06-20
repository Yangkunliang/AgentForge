"""Skill API 测试"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models.skill import Skill
from agent_forge.models.skill_install import SkillInstall
from agent_forge.skills.installer import SkillInstaller
from agent_forge.skills.manager import SkillManager


@pytest.mark.asyncio
class TestSkillManager:
    async def test_register_and_get_skill(self, db: AsyncSession):
        skill = await SkillManager.register_skill(
            db, "test-skill", "1.0.0", "Test skill", "test_skill.main"
        )
        assert skill.name == "test-skill"
        assert skill.version == "1.0.0"

        retrieved = await SkillManager.get_skill(db, "test-skill")
        assert retrieved is not None
        assert retrieved.name == "test-skill"

    async def test_list_skills(self, db: AsyncSession):
        await SkillManager.register_skill(
            db, "skill-1", "1.0.0", "Skill 1", "skill_1.main"
        )
        await SkillManager.register_skill(
            db, "skill-2", "2.0.0", "Skill 2", "skill_2.main"
        )

        skills = await SkillManager.list_skills(db)
        assert len(skills) >= 2

    async def test_unregister_skill(self, db: AsyncSession):
        await SkillManager.register_skill(
            db, "skill-to-delete", "1.0.0", "To delete", "delete.main"
        )

        success = await SkillManager.unregister_skill(db, "skill-to-delete")
        assert success is True

        retrieved = await SkillManager.get_skill(db, "skill-to-delete")
        assert retrieved is None


@pytest.mark.asyncio
class TestSkillInstaller:
    async def test_start_install(self, db: AsyncSession):
        install = SkillInstall(
            id="install-test-001",
            skill_name="skill",
            source="git+https://github.com/test/skill.git",
            version="latest",
            status="pending",
            log="",
            error=None,
        )
        db.add(install)
        await db.commit()

        assert install.status == "pending"
        assert install.skill_name == "skill"

    async def test_get_install_status(self, db: AsyncSession):
        install = SkillInstall(
            id="install-test-002",
            skill_name="test-package",
            source="test-package",
            version="latest",
            status="pending",
            log="",
            error=None,
        )
        db.add(install)
        await db.commit()

        retrieved = await SkillInstaller.get_install_status(db, install.id)
        assert retrieved is not None
        assert retrieved.id == install.id

    async def test_extract_skill_name(self):
        assert SkillInstaller._extract_skill_name("git+https://github.com/user/skill-name.git") == "skill-name"
        assert SkillInstaller._extract_skill_name("my-package@1.0.0") == "my-package"
        assert SkillInstaller._extract_skill_name("simple-package") == "simple-package"