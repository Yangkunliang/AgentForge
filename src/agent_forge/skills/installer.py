"""Skill 安装器 - 支持从 Git/PyPI/GitHub URL 安装 Skill"""

from __future__ import annotations

import asyncio
import inspect
import importlib.util
import logging
import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models.skill_install import SkillInstall
from agent_forge.skills.manifest import SkillImportPreview, SkillManifestError, load_skill_manifest
from agent_forge.skills.manager import SkillManager
from agent_forge.skills.registry import get_skill_registry

logger = logging.getLogger(__name__)

# 安装目录
SKILLS_INSTALLED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "skills" / "installed"


class SkillInstaller:
    _install_tasks: dict[str, dict] = {}

    @classmethod
    async def preview_import(cls, source: str, version: str | None = None) -> SkillImportPreview:
        source_type = cls._detect_source_type(source)
        if source_type == "local":
            return load_skill_manifest(Path(source), source=source, source_type="local")
        if source_type in {"github", "git"}:
            return await cls._preview_from_git_source(source, version, source_type)
        if source_type == "pypi":
            return await cls._preview_from_pypi_source(source, version)
        raise SkillManifestError(f"Unsupported Skill source type: {source_type}")

    @classmethod
    async def install_from_source(
        cls,
        db: AsyncSession,
        source: str,
        version: str | None = None,
        *,
        confirm_risk: bool = False,
    ) -> SkillInstall:
        source_type = cls._detect_source_type(source)
        preview = await cls.preview_import(source, version)
        if preview.requires_confirmation and not confirm_risk:
            raise PermissionError("High-risk Skill import requires explicit confirmation")

        if source_type != "local":
            return await cls.start_install(db, source, version, preview=preview)

        install_id = f"install-{uuid4().hex[:8]}"
        install_task = SkillInstall(
            id=install_id,
            skill_name=preview.name,
            source=source,
            version=version or preview.version,
            status="installing",
            log="Starting validated installation...\n",
            error=None,
            manifest_hash=preview.manifest_hash,
            permissions=preview.permissions,
            risk_level=preview.risk_level,
            preview=preview.to_dict(),
        )
        db.add(install_task)
        await db.commit()

        try:
            await cls._install_local_preview(db, install_task, Path(source), preview)
            install_task.status = "done"
            install_task.log += f"Installed skill '{preview.name}' successfully.\n"
            await db.commit()
        except Exception as exc:
            install_task.status = "failed"
            install_task.error = str(exc)
            install_task.log += f"Installation failed: {exc}\n"
            await db.commit()
            raise
        return install_task

    @classmethod
    async def start_install(
        cls,
        db: AsyncSession,
        source: str,
        version: str | None = None,
        preview: SkillImportPreview | None = None,
    ) -> SkillInstall:
        install_id = f"install-{uuid4().hex[:8]}"
        skill_name = preview.name if preview else cls._extract_skill_name(source)

        install_task = SkillInstall(
            id=install_id,
            skill_name=skill_name,
            source=source,
            version=version or (preview.version if preview else "latest"),
            status="pending",
            log="",
            error=None,
            manifest_hash=preview.manifest_hash if preview else None,
            permissions=preview.permissions if preview else [],
            risk_level=preview.risk_level if preview else None,
            preview=preview.to_dict() if preview else {},
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
            elif source_type == "local":
                preview = await cls.preview_import(source, version)
                await cls._install_local_preview(db, install_record, Path(source), preview)
                install_record.status = "done"
                install_record.log += f"Installed skill '{preview.name}' successfully.\n"
                await db.commit()
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

            manifest_dir = cls._find_manifest_dir(temp_dir / "repo")
            if not manifest_dir:
                raise RuntimeError("No agentforge-skill.yaml or skill.md found in repository")

            preview = load_skill_manifest(manifest_dir, source=repo_url, source_type="github")
            install_record.log += f"Found manifest for skill '{preview.name}' at {manifest_dir}...\n"
            await cls._install_local_preview(db, install_record, manifest_dir, preview)

            install_record.status = "done"
            install_record.log += f"\nInstalled skill '{preview.name}' successfully.\n"

        except Exception as e:
            raise RuntimeError(f"GitHub install failed: {e!s}") from e
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        await db.commit()

    @classmethod
    async def _install_local_preview(
        cls,
        db: AsyncSession,
        install_record: SkillInstall,
        source_dir: Path,
        preview: SkillImportPreview,
    ) -> None:
        installed_dir = SKILLS_INSTALLED_DIR / preview.name
        if installed_dir.exists():
            shutil.rmtree(installed_dir, ignore_errors=True)
        installed_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, installed_dir, ignore=shutil.ignore_patterns("__pycache__", ".git"))

        install_record.skill_name = preview.name
        install_record.version = preview.version
        install_record.manifest_hash = preview.manifest_hash
        install_record.permissions = preview.permissions
        install_record.risk_level = preview.risk_level
        install_record.preview = preview.to_dict()
        install_record.log += f"Copied skill to {installed_dir}.\n"

        entry_point = preview.executor_entry_point
        executor = cls._load_local_executor(installed_dir, entry_point)
        executors = {}
        if executor is not None:
            for tool_def in preview.tool_defs:
                executors[tool_def["function"]["name"]] = executor

        await SkillManager.register_skill(
            db,
            name=preview.name,
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
        get_skill_registry().register(
            skill_name=preview.name,
            tool_defs=preview.tool_defs,
            executors=executors,
            runtime_spec=preview.runtime_spec,
        )

    @staticmethod
    def _load_local_executor(installed_dir: Path, entry_point: str | None):
        if not entry_point:
            return None
        module_name, _, function_name = entry_point.partition(":")
        if not module_name or not function_name:
            raise RuntimeError("executor.entry_point must use module:function format")

        module_path = installed_dir / Path(*module_name.split(".")).with_suffix(".py")
        if not module_path.exists():
            raise RuntimeError(f"executor module not found: {module_path}")

        safe_module = re.sub(r"[^a-zA-Z0-9_]", "_", f"agentforge_skill_{installed_dir.name}_{module_name}")
        spec = importlib.util.spec_from_file_location(safe_module, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"failed to load executor module: {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[safe_module] = module
        spec.loader.exec_module(module)
        fn = getattr(module, function_name, None)
        if fn is None:
            raise RuntimeError(f"executor function not found: {function_name}")

        async def wrapped_executor(**kwargs):
            result = fn(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result

        return wrapped_executor

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

            manifest_dir = cls._find_manifest_dir(temp_dir / "repo")
            if not manifest_dir:
                raise RuntimeError("No agentforge-skill.yaml or skill.md found in repository")

            preview = load_skill_manifest(manifest_dir, source=repo_url, source_type="git")
            await cls._install_local_preview(db, install_record, manifest_dir, preview)
            install_record.status = "done"
            install_record.log += f"Installed skill '{preview.name}' from {repo_url}.\n"
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
    def _find_manifest_dir(parent: Path) -> Path | None:
        for filename in ("agentforge-skill.yaml", "skill.md"):
            direct = parent / filename
            if direct.exists():
                return parent
        for entry in parent.rglob("agentforge-skill.yaml"):
            if entry.is_file():
                return entry.parent
        skill_md = SkillInstaller._find_skill_md(parent)
        return skill_md.parent if skill_md else None

    @classmethod
    async def _preview_from_git_source(
        cls,
        repo_url: str,
        version: str | None,
        source_type: str,
    ) -> SkillImportPreview:
        temp_dir = Path(f"/tmp/agentforge-skill-preview-{uuid4().hex[:8]}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            cmd = ["git", "clone", "--depth", "1"]
            if version and version != "latest":
                cmd.extend(["--branch", version])
            cmd.extend([repo_url, str(temp_dir / "repo")])
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise SkillManifestError(f"git clone failed: {stderr.decode(errors='replace')}")
            manifest_dir = cls._find_manifest_dir(temp_dir / "repo")
            if not manifest_dir:
                raise SkillManifestError("Skill manifest not found in repository")
            return load_skill_manifest(manifest_dir, source=repo_url, source_type=source_type)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    async def _preview_from_pypi_source(cls, package_name: str, version: str | None) -> SkillImportPreview:
        temp_dir = Path(f"/tmp/agentforge-skill-pypi-preview-{uuid4().hex[:8]}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            package_spec = f"{package_name}=={version}" if version else package_name
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pip",
                "download",
                "--no-deps",
                "--dest",
                str(temp_dir),
                package_spec,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise SkillManifestError(f"pip download failed: {stderr.decode(errors='replace')}")

            archive = next(temp_dir.iterdir(), None)
            if archive is None:
                raise SkillManifestError("pip download did not produce a package archive")
            extract_dir = temp_dir / "extract"
            extract_dir.mkdir()
            if archive.suffix == ".whl":
                with zipfile.ZipFile(archive) as zf:
                    cls._safe_extract_zip(zf, extract_dir)
            else:
                with tarfile.open(archive) as tf:
                    cls._safe_extract_tar(tf, extract_dir)
            manifest_dir = cls._find_manifest_dir(extract_dir)
            if not manifest_dir:
                raise SkillManifestError("Skill manifest not found in PyPI package")
            return load_skill_manifest(manifest_dir, source=package_name, source_type="pypi")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _safe_extract_zip(zf: zipfile.ZipFile, destination: Path) -> None:
        destination_root = destination.resolve()
        for member in zf.infolist():
            target = (destination / member.filename).resolve()
            if destination_root != target and destination_root not in target.parents:
                raise SkillManifestError("Package archive contains unsafe paths")
        zf.extractall(destination)

    @staticmethod
    def _safe_extract_tar(tf: tarfile.TarFile, destination: Path) -> None:
        destination_root = destination.resolve()
        for member in tf.getmembers():
            if member.issym() or member.islnk():
                raise SkillManifestError("Package archive contains links")
            target = (destination / member.name).resolve()
            if destination_root != target and destination_root not in target.parents:
                raise SkillManifestError("Package archive contains unsafe paths")
        try:
            tf.extractall(destination, filter="data")
        except TypeError:
            tf.extractall(destination)

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
