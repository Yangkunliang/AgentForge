"""本地 Skill 热加载器

启动时扫描 `skills/` 目录下所有子目录中的 `skill.md` 文件，
解析 manifest 并注册到数据库。
放置 skill.md 到目录即自动注册，无需重启。
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.skills.manifest import parse_skill_md, to_tool_def
from agent_forge.skills.manager import SkillManager

logger = logging.getLogger(__name__)

# 默认 skills 目录（相对于项目根目录）
DEFAULT_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "skills")


class SkillLoader:
    """从本地目录扫描并注册 skill.md 文件"""

    def __init__(self, skills_dir: str | None = None):
        self.skills_dir = Path(skills_dir) if skills_dir else Path(DEFAULT_SKILLS_DIR)
        # 支持的两个子目录
        self.subdirs = ["market", "user", "installed"]

    async def load_all(self, db: AsyncSession) -> list[str]:
        """扫描 skills_dir/ 下所有 skill.md 并注册。

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

                skill_md = entry / "skill.md"
                if not skill_md.exists():
                    logger.debug("No skill.md in %s, skipping", entry)
                    continue

                try:
                    name = await self._register_from_file(db, skill_md, str(entry))
                    if name:
                        registered.append(name)
                        logger.info("Loaded skill '%s' from %s", name, skill_md)
                except Exception as e:
                    logger.warning("Failed to load skill from %s: %s", entry, e)

        return registered

    async def _register_from_file(
        self,
        db: AsyncSession,
        skill_md_path: Path,
        skill_dir: str,
    ) -> str | None:
        """解析单个 skill.md 并注册到 DB。

        如果 skill 已存在则跳过，否则创建新记录。
        entry_point 根据目录下是否存在 executor.py 设置。
        """
        content = skill_md_path.read_text(encoding="utf-8")
        parsed = parse_skill_md(content)
        name = parsed.get("name")
        if not name:
            # 从目录名推断
            name = skill_md_path.parent.name
            logger.info("No name in frontmatter, using directory name: %s", name)

        # 检查是否已注册
        existing = await SkillManager.get_skill(db, name)
        if existing:
            logger.debug("Skill '%s' already registered, skipping", name)
            return name

        # 构建 manifest
        manifest: dict[str, Any] = {
            "name": name,
            "version": parsed.get("version", "1.0.0"),
            "description": parsed.get("description", ""),
        }

        # 尝试从 manifest 中提取 tool 定义
        raw_fm = parsed.get("raw_frontmatter", {})
        # 如果 skill.md body 中有 ## Tool Definition 部分，尝试解析
        body = parsed.get("body", "")
        tool_match = re.search(r"##\s*Tool Definition\s*\n```yaml\s*\n(.*?)```", body, re.DOTALL)
        if tool_match:
            # 简单解析 YAML 块为 tool 格式
            tool_yaml = tool_match.group(1)
            tool_spec = self._parse_tool_yaml(tool_yaml)
            if tool_spec:
                manifest["tool"] = tool_spec

        # 确定 entry_point
        executor_py = Path(skill_dir) / "executor.py"
        entry_point: str | None = None
        if executor_py.exists():
            entry_point = f"{name}.executor"

        await SkillManager.register_skill(
            db,
            name=name,
            version=str(manifest.get("version", "1.0.0")),
            description=str(manifest.get("description", "")),
            entry_point=entry_point,
            manifest=manifest,
        )

        # 复制到 market 目录作为备份
        market_dir = self.skills_dir / "market" / name
        if market_dir.exists():
            shutil.rmtree(market_dir)
        shutil.copytree(skill_dir, str(market_dir))

        return name

    @staticmethod
    def _parse_tool_yaml(yaml_text: str) -> dict | None:
        """从 skill.md 中的 ## Tool Definition YAML 块解析 tool 定义。

        简单解析 key: value 格式，不支持嵌套复杂结构。
        """
        lines = yaml_text.strip().split("\n")
        tool: dict[str, Any] = {}
        current_key: str | None = None
        current_obj: dict[str, Any] | None = None

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())

            if indent == 0:
                # 顶层 key
                if ":" in stripped:
                    key, _, value = stripped.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if value:
                        tool[key] = value
                        current_key = key
                        current_obj = None
                    else:
                        current_key = key
                        current_obj = {}
            elif current_key and current_obj is not None:
                if ":" in stripped:
                    key, _, value = stripped.partition(":")
                    current_obj[key.strip()] = value.strip().strip('"').strip("'")

        if not tool:
            return None

        # 标准化为 OpenAI tools format
        name = tool.get("name", "unknown")
        description = tool.get("description", "")
        tool.setdefault("tool", {
            "name": name,
            "description": description,
            "parameters": current_obj or {},
        })

        return tool["tool"]


# 需要 re 导入
import re as _re

# 模块级重新导出（避免循环导入）
__all__ = ["SkillLoader", "DEFAULT_SKILLS_DIR"]
