"""审计日志表 (AuditLog)

记录系统中所有关键操作的审计日志,包括操作类型、资源、用户、追踪 ID、执行状态等。
用于安全审计、问题排查和合规性检查。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    """审计日志表 — 记录系统中所有关键操作的审计追踪。

    每次 API 请求、Agent 执行、Skill 调用等都写入一条审计日志。
    包含 trace_id 便于跨服务链路追踪,degraded 标记是否触发了降级。

    Fields:
        action: 操作类型(如 "task.create", "skill.install")
        resource: 被操作资源类型(如 "task", "agent", "skill")
        user_id: 操作用户 ID
        trace_id: 全链路追踪 ID
        status: 操作结果状态
        degraded: 是否触发了降级策略
        details: 附加详情(JSON)
        created_at: 操作时间
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # 主键

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # 操作类型

    resource: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 资源类型

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # 操作用户 ID

    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # 全链路追踪 ID

    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 执行状态

    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否降级

    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 操作详情
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"
