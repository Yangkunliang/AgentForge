"""Skill 安装器 - 支持从 Git/PyPI/GitHub URL 安装 Skill"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models.skill_install import SkillInstall
from agent_forge.skills.manager import SkillManager

logger = logging.getLogger(__name__)

# 安装目录
SKILLS_INSTALLED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "skills" / "installed"


class SkillInstaller:
    _install_tasks: dict[str, dict] = {}

    @classmethod
    async def start_install(
        cls, db: AsyncSession, source: str, version: str | None = None
    ) -> SkillInstall:
        install_id = f"install-{uuid4().hex[:8]}"
        skill_name = cls._extract_skill_name(source)

        install_task = SkillInstall(
            id=install_id,
            skill_name=skill_name,
            source=source,
            version=version or "latest",
            status="pending",
            log="",
            error=None,
        )
        db.add(install_task)
        await db.commit()

        cls._install_tasks[install_id] = {"status": "installing", "log": ""}

        asyncio.create_task(cls._run_install(db, install_id, source, version))

        return install_task

    @classmethod
    async def get_install_status(cls, db: AsyncSession, install_id: str) -> SkillInstall | None:
        result = await db.execute(select(SkillInstall).where(SkillInstall.id == install_id))
        return result.scalar_one_or_none()

    @classmethod
    async def uninstall_skill(cls, db: AsyncSession, skill_name: str) -> bool:
        # 尝试 pip uninstall
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "uninstall", skill_name, "-y",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            await proc.communicate()
        except Exception as e:
            logger.error(f"Failed to pip uninstall skill {skill_name}: {e}")

        # 清理本地安装目录
        installed_dir = SKILLS_INSTALLED_DIR / skill_name
        if installed_dir.exists():
            shutil.rmtree(installed_dir, ignore_errors=True)

        return True

    @classmethod
    async def _run_install(
        cls, db: AsyncSession, install_id: str, source: str, version: str | None
    ) -> None:
        """自动识别安装源类型并执行相应安装逻辑"""
        try:
            install_record = await cls.get_install_status(db, install_id)
            if not install_record:
                return

            install_record.status = "installing"
            install_record.log = "Starting installation...\n"
            await db.commit()

            source_type = cls._detect_source_type(source)
            logger.info("Detected source type '%s' for '%s'", source_type, source)

            if source_type == "github":
                await cls._install_from_github(db, install_id, source, version)
            elif source_type == "git":
                await cls._install_from_git(db, install_id, source, version)
            else:
                # 默认走 pip（PyPI 包名或本地路径）
                await cls._install_pypi(db, install_id, source, version)

        except Exception as e:
            logger.exception("Install task %s failed: %s", install_id, e)
            try:
                install_record = await cls.get_install_status(db, install_id)
                if install_record:
                    install_record.status = "failed"
                    install_record.error = str(e)
                    await db.commit()
            except Exception:
                pass

    @staticmethod
    def _detect_source_type(source: str) -> str:
        """自动识别安装源类型"""
        if source.startswith("git+https://github.com"):
            return "github"
        if source.startswith("https://github.com"):
            return "github"
        if source.startswith("git+") or source.startswith("https://gitlab.com"):
            return "git"
        if os.path.exists(source):
            return "local"
        return "pypi"

    @classmethod
    async def _install_from_github(
        cls,
        db: AsyncSession,
        install_id: str,
        repo_url: str,
        version: str | None,
    ) -> None:
        """Clone GitHub repo → 解析 skill.md → 保存到 skills/installed/<name>/"""
        install_record = await cls.get_install_status(db, install_id)
        if not install_record:
            return

        temp_dir = Path("/tmp/agentforge-skill-install")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 确定 clone URL 和 ref
        if version and version != "latest":
            clone_url = repo_url
            ref = version
        else:
            clone_url = repo_url
            ref = None

        install_record.log += f"Cloning {repo_url}...\n"
        await db.commit()

        try:
            cmd = ["git", "clone", "--depth", "1"]
            if ref:
                cmd.extend(["--branch", ref])
            cmd.append(clone_url)
            cmd.append(str(temp_dir / "repo"))

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f"git clone failed: {stderr.decode()}")

            repo_dir = temp_dir / "repo"

            # 递归搜索 skill.md
            skill_md = cls._find_skill_md(repo_dir)
            if not skill_md:
                raise RuntimeError("No skill.md found in repository")

            install_record.log += f"Found skill.md at {skill_md}...\n"
            await db.commit()

            # 解析 manifest
            from agent_forge.skills.manifest import parse_skill_md
            content = skill_md.read_text(encoding="utf-8")
            parsed = parse_skill_md(content)
            name = parsed.get("name") or skill_md.parent.name

            # 创建安装目录
            installed_dir = SKILLS_INSTALLED_DIR / name
            installed_dir.mkdir(parents=True, exist_ok=True)

            # 复制 skill.md
            shutil.copy2(skill_md, installed_dir / "skill.md")

            # 复制同目录下其他文件（README, executor.py 等）
            for f in skill_md.parent.iterdir():
                if f.name != "skill.md":
                    shutil.copy2(f, installed_dir / f.name)

            install_record.log += f"Skill '{name}' copied to {installed_dir}...\n"
            await db.commit()

            # 注册到 DB
            manifest = {
                "name": name,
                "version": parsed.get("version", "1.0.0"),
                "description": parsed.get("description", ""),
            }
            raw_fm = parsed.get("raw_frontmatter", {})
            # 尝试从 body 提取 tool 定义
            body = parsed.get("body", "")
            import re
            tool_match = re.search(r"##\s*Tool Definition\s*\n```yaml\s*\n(.*?)```", body, re.DOTALL)
            if tool_match:
                tool_spec = SkillInstaller._parse_tool_yaml(tool_match.group(1))
                if tool_spec:
                    manifest["tool"] = tool_spec

            executor_py = installed_dir / "executor.py"
            entry_point = f"{name}.executor" if executor_py.exists() else None

            await SkillManager.register_skill(
                db,
                name=name,
                version=str(manifest.get("version", "1.0.0")),
                description=str(manifest.get("description", "")),
                entry_point=entry_point,
                manifest=manifest,
            )

            install_record.status = "done"
            install_record.log += f"\nInstalled skill '{name}' successfully.\n"

        except Exception as e:
            raise RuntimeError(f"GitHub install failed: {e!s}") from e
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        await db.commit()

    @classmethod
    async def _install_from_git(
        cls,
        db: AsyncSession,
        install_id: str,
        repo_url: str,
        version: str | None,
    ) -> None:
        """通用 Git repo 安装（非 GitHub）"""
        install_record = await cls.get_install_status(db, install_id)
        if not install_record:
            return

        temp_dir = Path("/tmp/agentforge-skill-install")
        temp_dir.mkdir(parents=True, exist_ok=True)

        install_record.log += f"Cloning {repo_url}...\n"
        await db.commit()

        try:
            cmd = ["git", "clone", "--depth", "1"]
            if version:
                cmd.extend(["--branch", version])
            cmd.append(repo_url)
            cmd.append(str(temp_dir / "repo"))

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f"git clone failed: {stderr.decode()}")

            repo_dir = temp_dir / "repo"
            skill_md = cls._find_skill_md(repo_dir)
            if not skill_md:
                raise RuntimeError("No skill.md found in repository")

            from agent_forge.skills.manifest import parse_skill_md
            content = skill_md.read_text(encoding="utf-8")
            parsed = parse_skill_md(content)
            name = parsed.get("name") or skill_md.parent.name

            installed_dir = SKILLS_INSTALLED_DIR / name
            installed_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_md, installed_dir / "skill.md")

            install_record.status = "done"
            install_record.log += f"Installed skill '{name}' from {repo_url}.\n"
            await db.commit()

            # 注册到 DB
            manifest = {
                "name": name,
                "version": parsed.get("version", "1.0.0"),
                "description": parsed.get("description", ""),
            }
            await SkillManager.register_skill(
                db,
                name=name,
                version=str(manifest.get("version", "1.0.0")),
                description=str(manifest.get("description", "")),
                entry_point=None,
                manifest=manifest,
            )
            await db.commit()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    async def _install_pypi(
        cls, db: AsyncSession, install_id: str, source: str, version: str | None
    ) -> None:
        """PyPI 包安装（保持原有逻辑）"""
        install_record = await cls.get_install_status(db, install_id)
        if not install_record:
            return

        args = [sys.executable, "-m", "pip", "install"]
        if version:
            args.append(f"{source}=={version}")
        else:
            args.append(source)

        install_record.log += f"Running: {' '.join(args)}\n"
        await db.commit()

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        log_lines = []
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            log_line = line.decode("utf-8", errors="replace").strip()
            log_lines.append(log_line)
            install_record.log = "\n".join(log_lines[-100:])
            await db.commit()

        await proc.wait()

        if proc.returncode == 0:
            install_record.status = "done"
            install_record.log += "\nInstallation completed successfully.\n"
        else:
            install_record.status = "failed"
            install_record.error = f"Installation failed with code {proc.returncode}"

        await db.commit()

    @staticmethod
    def _find_skill_md(parent: Path) -> Path | None:
        """在目录及其子目录中递归查找 skill.md"""
        skill_md = parent / "skill.md"
        if skill_md.exists():
            return skill_md
        for entry in parent.rglob("skill.md"):
            if entry.is_file():
                return entry
        return None

    @staticmethod
    def _parse_tool_yaml(yaml_text: str) -> dict | None:
        """从 skill.md 中的 YAML 块解析 tool 定义。

        简单解析 key: value 格式，返回 OpenAI tools format 结构。
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

        name = tool.get("name", "unknown")
        description = tool.get("description", "")
        return {
            "name": name,
            "description": description,
            "parameters": current_obj or {},
        }

    @staticmethod
    def _extract_skill_name(source: str) -> str:
        if source.startswith("git+"):
            parts = source.replace("git+", "").rstrip(".git").split("/")
            return parts[-1] if parts else "unknown"
        if source.startswith("https://github.com/"):
            parts = source.replace("https://github.com/", "").split("/")
            return parts[0] + "/" + parts[1] if len(parts) > 1 else parts[-1]
        if "@" in source:
            return source.split("@")[0]
        return source.split("/")[-1] if "/" in source else source
