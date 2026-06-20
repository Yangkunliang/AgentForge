"""数据导出任务模型"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ExportTask(Base, TimestampMixin):
    __tablename__ = "export_tasks"

    id: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="processing")
    total_records: Mapped[int] = mapped_column(default=0)
    estimated_size_mb: Mapped[float] = mapped_column(default=0.0)
    file_path: Mapped[str | None] = mapped_column(String(500))
    delevel: Mapped[str] = mapped_column(String(20), default="level_1")

    def __repr__(self) -> str:
        return f"<ExportTask id={self.id} type={self.type} status={self.status}>"