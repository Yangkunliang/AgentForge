"""数据导出管理器 - 创建、追踪、下载导出任务"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models.export_task import ExportTask
from agent_forge.models.task import Task
from agent_forge.models.task_execution import TaskExecution

logger = logging.getLogger(__name__)


class ExportManager:
    @classmethod
    async def create_export(
        cls,
        db: AsyncSession,
        export_type: str,
        start_date: str | None = None,
        end_date: str | None = None,
        delevel: str = "level_1",
    ) -> ExportTask:
        export_id = f"export-{uuid4().hex[:8]}"

        total_records = await cls._count_records(db, start_date, end_date)
        estimated_size = total_records * 0.5

        export_task = ExportTask(
            id=export_id,
            type=export_type,
            status="processing",
            total_records=total_records,
            estimated_size_mb=estimated_size,
            delevel=delevel,
        )
        db.add(export_task)
        await db.commit()

        asyncio.create_task(cls._run_export(db, export_id, start_date, end_date, delevel))

        return export_task

    @classmethod
    async def get_export(cls, db: AsyncSession, export_id: str) -> ExportTask | None:
        result = await db.execute(select(ExportTask).where(ExportTask.id == export_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_export_file_path(cls, db: AsyncSession, export_id: str) -> str | None:
        export = await cls.get_export(db, export_id)
        if export and export.status == "done" and export.file_path:
            return export.file_path
        return None

    @classmethod
    async def _run_export(
        cls, db: AsyncSession, export_id: str, start_date: str | None, end_date: str | None, delevel: str
    ) -> None:
        try:
            export = await cls.get_export(db, export_id)
            if not export:
                return

            query = select(Task)
            if start_date:
                query = query.where(Task.created_at >= start_date)
            if end_date:
                query = query.where(Task.created_at <= end_date)

            result = await db.execute(query)
            tasks = result.scalars().all()

            records = []
            from .anonymizer import DataAnonymizer

            for task in tasks:
                exec_result = await db.execute(
                    select(TaskExecution).where(TaskExecution.task_id == task.id)
                )
                executions = exec_result.scalars().all()

                record = {
                    "task_id": task.id,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "result": task.result,
                    "total_cost_usd": task.total_cost_usd,
                    "created_at": task.created_at,
                    "completed_at": task.completed_at,
                    "executions": [
                        {
                            "agent_id": e.agent_id,
                            "skill_id": e.skill_id,
                            "input": e.input,
                            "output": e.output,
                            "cost_usd": e.cost_usd,
                        }
                        for e in executions
                    ],
                }

                anonymized = DataAnonymizer.anonymize(record, delevel)
                records.append(anonymized)

            export_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "exports")
            os.makedirs(export_dir, exist_ok=True)

            file_path = os.path.join(export_dir, f"{export_id}.jsonl")
            with open(file_path, "w", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

            export.status = "done"
            export.file_path = file_path
            await db.commit()

            logger.info(f"Export {export_id} completed: {len(records)} records")

        except Exception as e:
            export = await cls.get_export(db, export_id)
            if export:
                export.status = "failed"
                await db.commit()
            logger.error(f"Export {export_id} failed: {e}")

    @classmethod
    async def _count_records(
        cls, db: AsyncSession, start_date: str | None, end_date: str | None
    ) -> int:
        query = select(Task)
        if start_date:
            query = query.where(Task.created_at >= start_date)
        if end_date:
            query = query.where(Task.created_at <= end_date)

        result = await db.execute(query)
        return len(result.scalars().all())