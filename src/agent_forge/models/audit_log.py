"""审计日志模型"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    """审计日志"""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"