"""Evaluation feedback event model."""

from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, JSON_VARIANT, TimestampMixin


class EvalEvent(Base, TimestampMixin):
    """Structured execution facts for long-term evaluation and optimization."""

    __tablename__ = "eval_events"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    pipeline_run_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    stage_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="success", index=True)

    agent_profile_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    agent_profile_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_route_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    model_route_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    skill_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    tool_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    artifact_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    delivery_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)

    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON_VARIANT, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<EvalEvent id={self.id} type={self.event_type} status={self.status}>"
