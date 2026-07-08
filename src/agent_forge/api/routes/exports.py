"""数据导出 API 路由"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.permissions import get_admin_user
from agent_forge.database import get_async_session
from agent_forge.exporter.manager import ExportManager
from agent_forge.models.export_task import ExportTask
from agent_forge.models.user import User

router = APIRouter(prefix="/exports", tags=["exports"])


class CreateExportRequest(BaseModel):
    type: str = "training_data"
    start_date: str | None = None
    end_date: str | None = None
    format: str = "jsonl"
    delevel: str = "level_1"


class ExportStatusResponse(BaseModel):
    export_id: str
    status: str
    total_records: int
    estimated_size_mb: float
    file_path: str | None


class ExportListResponse(BaseModel):
    total: int
    items: list[ExportStatusResponse]


def _export_to_response(export_task: ExportTask) -> ExportStatusResponse:
    return ExportStatusResponse(
        export_id=export_task.id,
        status=export_task.status,
        total_records=export_task.total_records,
        estimated_size_mb=round(export_task.estimated_size_mb, 2),
        file_path=export_task.file_path,
    )


@router.get("", response_model=ExportListResponse)
async def list_exports(
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_admin_user),
):
    export_tasks = await ExportManager.list_exports(db)
    items = [_export_to_response(task) for task in export_tasks]
    return ExportListResponse(total=len(items), items=items)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    request: CreateExportRequest,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_admin_user),
):
    export_task = await ExportManager.create_export(
        db, request.type, request.start_date, request.end_date, request.delevel
    )
    return {
        "export_id": export_task.id,
        "status": export_task.status,
        "total_records": export_task.total_records,
        "estimated_size_mb": round(export_task.estimated_size_mb, 2),
    }


@router.get("/{export_id}")
async def get_export_status(
    export_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_admin_user),
):
    export_task = await ExportManager.get_export(db, export_id)
    if not export_task:
        raise HTTPException(status_code=404, detail="Export task not found")

    return _export_to_response(export_task)


@router.get("/{export_id}/download")
async def download_export(
    export_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_admin_user),
):
    file_path = await ExportManager.get_export_file_path(db, export_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Export file not found")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Export file not found")

    filename = os.path.basename(file_path)
    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/x-ndjson",
    )
