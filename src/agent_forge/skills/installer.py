"""Skill 安装器 - 支持从 Git/PyPI 安装 Skill"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models.skill_install import SkillInstall

logger = logging.getLogger(__name__)


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
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "uninstall", skill_name, "-y",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception as e:
            logger.error(f"Failed to uninstall skill {skill_name}: {e}")
            return False

    @classmethod
    async def _run_install(
        cls, db: AsyncSession, install_id: str, source: str, version: str | None
    ) -> None:
        try:
            install_record = await cls.get_install_status(db, install_id)
            if not install_record:
                return

            install_record.status = "installing"
            install_record.log = "Starting installation...\n"
            await db.commit()

            args = [sys.executable, "-m", "pip", "install"]
            if version:
                args.append(f"{source}=={version}")
            else:
                args.append(source)

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

        except Exception as e:
            install_record = await cls.get_install_status(db, install_id)
            if install_record:
                install_record.status = "failed"
                install_record.error = str(e)
                await db.commit()
            logger.error(f"Install task {install_id} failed: {e}")

    @staticmethod
    def _extract_skill_name(source: str) -> str:
        if source.startswith("git+"):
            parts = source.replace("git+", "").rstrip(".git").split("/")
            return parts[-1] if parts else "unknown"
        if "@" in source:
            return source.split("@")[0]
        return source.split("/")[-1] if "/" in source else source