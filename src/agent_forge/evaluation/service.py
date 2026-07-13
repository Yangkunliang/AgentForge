"""Evaluation event recording and summary aggregation."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_forge.models import EvalEvent, Project

logger = logging.getLogger(__name__)


class EvaluationService:
    """Low-friction event sink for execution quality feedback."""

    @staticmethod
    async def record_event(
        db: AsyncSession,
        *,
        project_id: str | None = None,
        pipeline_run_id: str | None = None,
        stage_id: str | None = None,
        event_type: str,
        status: str = "success",
        agent_profile_id: str | None = None,
        agent_profile_name: str | None = None,
        model_route_key: str | None = None,
        model_route_name: str | None = None,
        model_name: str | None = None,
        skill_name: str | None = None,
        tool_name: str | None = None,
        artifact_id: str | None = None,
        delivery_channel: str | None = None,
        latency_ms: int | None = None,
        cost_usd: float = 0.0,
        tokens_used: int | None = None,
        failure_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvalEvent:
        event = EvalEvent(
            id=f"eval-{uuid.uuid4().hex[:16]}",
            project_id=project_id,
            pipeline_run_id=pipeline_run_id,
            stage_id=stage_id,
            event_type=event_type,
            status=status,
            agent_profile_id=agent_profile_id,
            agent_profile_name=agent_profile_name,
            model_route_key=model_route_key,
            model_route_name=model_route_name,
            model_name=model_name,
            skill_name=skill_name,
            tool_name=tool_name,
            artifact_id=artifact_id,
            delivery_channel=delivery_channel,
            latency_ms=latency_ms,
            cost_usd=float(cost_usd or 0.0),
            tokens_used=tokens_used,
            failure_reason=failure_reason,
            metadata_json=metadata or {},
        )
        db.add(event)
        await db.flush()
        return event

    @staticmethod
    async def safe_record_event(
        session_factory: async_sessionmaker[AsyncSession],
        **kwargs: Any,
    ) -> EvalEvent | None:
        try:
            async with session_factory() as db:
                event = await EvaluationService.record_event(db, **kwargs)
                await db.commit()
                return event
        except Exception:
            logger.warning("Evaluation event write failed", exc_info=True)
            return None

    @staticmethod
    async def get_summary(
        db: AsyncSession,
        *,
        user_id: str | None = None,
        project_id: str | None = None,
        pipeline_run_id: str | None = None,
        start_date: datetime | str | None = None,
        end_date: datetime | str | None = None,
    ) -> dict[str, Any]:
        stmt = select(EvalEvent)
        if user_id:
            stmt = stmt.join(Project, EvalEvent.project_id == Project.id).where(Project.user_id == user_id)
        if project_id:
            stmt = stmt.where(EvalEvent.project_id == project_id)
        if pipeline_run_id:
            stmt = stmt.where(EvalEvent.pipeline_run_id == pipeline_run_id)
        if start_date:
            stmt = stmt.where(EvalEvent.created_at >= start_date)
        if end_date:
            stmt = stmt.where(EvalEvent.created_at <= end_date)
        stmt = stmt.order_by(EvalEvent.created_at.asc())

        result = await db.execute(stmt)
        events = list(result.scalars().all())

        return {
            "project_id": project_id,
            "pipeline_run_id": pipeline_run_id,
            "total_events": len(events),
            "period": {
                "start_date": start_date.isoformat() if isinstance(start_date, datetime) else start_date,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime) else end_date,
            },
            "pipelines": _metric_block([event for event in events if event.event_type.startswith("pipeline_")]),
            "stages": _metric_block([event for event in events if event.event_type.startswith("stage_")]),
            "skills": _metric_block([event for event in events if event.event_type.startswith("skill_")]),
            "delivery": _metric_block([event for event in events if event.event_type.startswith("delivery_")]),
            "artifacts": _artifact_block(events),
            "confirmations": _confirmation_block(events),
            "skill_authorizations": _skill_authorization_block(events),
            "agents": _group_by_dimension(events, "agent_profile_id", "agent_profile_name"),
            "models": _group_by_dimension(events, "model_route_key", "model_route_name"),
            "event_counts": _event_counts(events),
        }


def _metric_block(events: list[EvalEvent]) -> dict[str, Any]:
    total = len(events)
    succeeded = sum(1 for event in events if _is_success(event))
    failed = sum(1 for event in events if _is_failure(event))
    return {
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "success_rate": round(succeeded / total, 4) if total else 0.0,
        "average_latency_ms": _average_latency(events),
    }


def _artifact_block(events: list[EvalEvent]) -> dict[str, int]:
    return {
        "generated": sum(1 for event in events if event.event_type == "artifact_created"),
        "delivered": sum(1 for event in events if event.artifact_id and event.event_type == "delivery_succeeded"),
        "failed": sum(1 for event in events if event.artifact_id and _is_failure(event)),
    }


def _confirmation_block(events: list[EvalEvent]) -> dict[str, Any]:
    confirmation_events = [event for event in events if event.event_type.startswith("confirmation_")]
    revised = sum(1 for event in confirmation_events if event.event_type in {"confirmation_revised", "confirmation_revise"})
    return {
        "total": len(confirmation_events),
        "revised": revised,
        "revise_ratio": round(revised / len(confirmation_events), 4) if confirmation_events else 0.0,
    }


def _skill_authorization_block(events: list[EvalEvent]) -> dict[str, Any]:
    authorization_events = [
        event
        for event in events
        if event.event_type in {"skill_authorization_required", "skill_authorization_granted"}
    ]
    required_events = [
        event for event in authorization_events if event.event_type == "skill_authorization_required"
    ]
    granted_events = [
        event for event in authorization_events if event.event_type == "skill_authorization_granted"
    ]
    required = len(required_events)
    granted = len(granted_events)
    return {
        "required": required,
        "granted": granted,
        "grant_rate": _rate(granted, required),
        "by_skill": _authorization_group_by_skill(required_events, granted_events),
        "by_permission": _authorization_group_by_permission(required_events, granted_events),
    }


def _authorization_group_by_skill(
    required_events: list[EvalEvent],
    granted_events: list[EvalEvent],
) -> list[dict[str, Any]]:
    keys = _ordered_unique(
        [
            event.skill_name
            for event in [*required_events, *granted_events]
            if event.skill_name
        ]
    )
    rows: list[dict[str, Any]] = []
    for skill_name in keys:
        required = sum(1 for event in required_events if event.skill_name == skill_name)
        granted = sum(1 for event in granted_events if event.skill_name == skill_name)
        rows.append(
            {
                "skill_name": skill_name,
                "required": required,
                "granted": granted,
                "grant_rate": _rate(granted, required),
            }
        )
    return sorted(rows, key=lambda row: (-row["required"], -row["granted"], row["skill_name"]))


def _authorization_group_by_permission(
    required_events: list[EvalEvent],
    granted_events: list[EvalEvent],
) -> list[dict[str, Any]]:
    required_counts = _permission_counts(required_events)
    granted_counts = _permission_counts(granted_events)
    keys = _ordered_unique([*required_counts.keys(), *granted_counts.keys()])
    rows: list[dict[str, Any]] = []
    for permission in keys:
        required = required_counts.get(permission, 0)
        granted = granted_counts.get(permission, 0)
        rows.append(
            {
                "permission": permission,
                "required": required,
                "granted": granted,
                "grant_rate": _rate(granted, required),
            }
        )
    return sorted(rows, key=lambda row: (-row["required"], -row["granted"], row["permission"]))


def _permission_counts(events: list[EvalEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        permissions = (event.metadata_json or {}).get("permissions")
        if not isinstance(permissions, list):
            continue
        for permission in permissions:
            if not isinstance(permission, str) or not permission:
                continue
            counts[permission] = counts.get(permission, 0) + 1
    return counts


def _group_by_dimension(events: list[EvalEvent], id_attr: str, name_attr: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[EvalEvent]] = defaultdict(list)
    for event in events:
        key = getattr(event, id_attr)
        if key:
            grouped[str(key)].append(event)

    rows: list[dict[str, Any]] = []
    for key, group in grouped.items():
        failed = sum(1 for event in group if _is_failure(event))
        name = next((getattr(event, name_attr) for event in group if getattr(event, name_attr)), None)
        row_key = id_attr
        rows.append({
            row_key: key,
            "name": name,
            "usage_count": len(group),
            "failed": failed,
            "failure_rate": round(failed / len(group), 4) if group else 0.0,
            "average_latency_ms": _average_latency(group),
            "cost_usd": round(sum(float(event.cost_usd or 0.0) for event in group), 6),
        })
    return sorted(rows, key=lambda row: row["usage_count"], reverse=True)


def _event_counts(events: list[EvalEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
    return counts


def _average_latency(events: list[EvalEvent]) -> float:
    latencies = [event.latency_ms for event in events if event.latency_ms is not None]
    return round(sum(latencies) / len(latencies), 2) if latencies else 0.0


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _ordered_unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _is_success(event: EvalEvent) -> bool:
    return event.status == "success" or event.event_type.endswith("_completed") or event.event_type.endswith("_succeeded")


def _is_failure(event: EvalEvent) -> bool:
    return event.status == "failed" or event.event_type.endswith("_failed")
