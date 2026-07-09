"""本地 Skill 热加载器

启动时扫描 `skills/` 目录下所有子目录中的 `agentforge-skill.yaml` 或 `skill.md` 文件，
解析 manifest 并注册到数据库。
放置 manifest 到目录即自动注册，无需重启。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.skills.manifest import load_skill_manifest
from agent_forge.skills.manager import SkillManager

logger = logging.getLogger(__name__)

# 默认 skills 目录（相对于项目根目录）
DEFAULT_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "skills")


class SkillLoader:
    """从本地目录扫描并注册 Skill manifest 文件"""

    def __init__(self, skills_dir: str | None = None):
        self.skills_dir = Path(skills_dir) if skills_dir else Path(DEFAULT_SKILLS_DIR)
        # 支持的两个子目录
        self.subdirs = ["market", "user", "installed"]

    async def load_all(self, db: AsyncSession) -> list[str]:
        """扫描 skills_dir/ 下所有 Skill manifest 并注册。

        返回已注册的 skill 名称列表。
        """
        registered: list[str] = []

        if not self.skills_dir.exists():
            logger.info("Skills directory %s does not exist, skipping", self.skills_dir)
            return registered

        # 遍历所有支持的子目录
        for subdir in self.subdirs:
            subdir_path = self.skills_dir / subdir
            if not subdir_path.is_dir():
                continue

            # 遍历子目录下的每个 skill 目录
            for entry in sorted(subdir_path.iterdir()):
                if not entry.is_dir():
                    continue

                manifest_path = self._find_manifest_path(entry)
                if not manifest_path:
                    logger.debug("No Skill manifest in %s, skipping", entry)
                    continue

                try:
                    name = await self._register_from_file(db, manifest_path, str(entry))
                    if name:
                        registered.append(name)
                        logger.info("Loaded skill '%s' from %s", name, manifest_path)
                except Exception as e:
                    logger.warning("Failed to load skill from %s: %s", entry, e)

        return registered

    @staticmethod
    def _find_manifest_path(skill_dir: Path) -> Path | None:
        for filename in ("agentforge-skill.yaml", "skill.md"):
            path = skill_dir / filename
            if path.exists():
                return path
        return None

    async def _register_from_file(
        self,
        db: AsyncSession,
        manifest_path: Path,
        skill_dir: str,
    ) -> str | None:
        """解析单个 Skill manifest 并注册到 DB。

        如果 skill 已存在则跳过，否则创建新记录。
        entry_point 根据目录下是否存在 executor.py 设置。
        """
        preview = load_skill_manifest(manifest_path.parent, source=skill_dir)
        name = preview.name

        # 检查是否已注册
        existing = await SkillManager.get_skill(db, name)
        if existing:
            logger.debug("Skill '%s' already registered, skipping", name)
            return name

        # 确定 entry_point
        executor_py = Path(skill_dir) / "executor.py"
        entry_point: str | None = None
        if executor_py.exists():
            entry_point = preview.executor_entry_point or "executor:run"

        await SkillManager.register_skill(
            db,
            name=name,
            version=preview.version,
            description=preview.description,
            entry_point=entry_point,
            manifest={
                "name": preview.name,
                "version": preview.version,
                "description": preview.description,
                "tools": preview.tools,
                "permissions": preview.permissions,
            },
            manifest_hash=preview.manifest_hash,
            permissions=preview.permissions,
            runtime_spec=preview.runtime_spec,
            audit_level=preview.audit_level,
            source_type=preview.source_type,
        )

        return name

# 模块级重新导出（避免循环导入）
__all__ = ["SkillLoader", "DEFAULT_SKILLS_DIR"]
