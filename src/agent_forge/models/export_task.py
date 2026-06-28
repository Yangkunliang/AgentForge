"""数据导出任务表 (ExportTask)

存储异步数据导出任务的执行状态和结果。
支持将任务日志、记忆数据等导出为 JSONL 等格式,供训练数据生成或合规用途。
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ExportTask(Base, TimestampMixin):
    """数据导出任务表 — 跟踪异步导出任务的进度和结果。

    当用户请求导出任务日志、记忆数据等时,生成一条记录跟踪导出进度。
    delevel 字段控制数据扁平化层级。

    Fields:
        type: 导出类型(如 "jsonl", "training_data")
        status: 执行状态: processing / completed / failed
        total_records: 总记录数
        estimated_size_mb: 预估文件大小(MB)
        file_path: 导出文件的存储路径
        delevel: 数据扁平化层级
    """
    __tablename__ = "export_tasks"

    id: Mapped[str] = mapped_column(primary_key=True)  # 主键

    type: Mapped[str] = mapped_column(String(50))  # 导出类型

    status: Mapped[str] = mapped_column(String(20), default="processing")  # 执行状态

    total_records: Mapped[int] = mapped_column(default=0)  # 总记录数

    estimated_size_mb: Mapped[float] = mapped_column(default=0.0)  # 预估文件大小(MB)

    file_path: Mapped[str | None] = mapped_column(String(500))  # 导出文件路径

    delevel: Mapped[str] = mapped_column(String(20), default="level_1")  # 数据扁平化层级

    def __repr__(self) -> str:
        return f"<ExportTask id={self.id} type={self.type} status={self.status}>"
