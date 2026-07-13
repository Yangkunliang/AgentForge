"""Compatibility re-exports for the Dashboard API route.

The active application mounts ``api.routes.dashboard``. This module keeps the
older ``agent_forge.api.routes.dashboard`` import path available without
duplicating Dashboard business logic.
"""

from __future__ import annotations

from api.routes.dashboard import (
    AgentStats,
    CostStats,
    DailyCost,
    DashboardResponse,
    EvaluationStats,
    RecentTask,
    SkillAuthorizationByPermission,
    SkillAuthorizationBySkill,
    SkillAuthorizationDimension,
    SkillAuthorizationStats,
    SkillStats,
    TaskStats,
    _agent_stats,
    _cost_stats,
    _get_evaluation_stats,
    _recent_tasks,
    _skill_stats,
    _task_stats,
    router,
)

_get_task_stats = _task_stats
_get_agent_stats = _agent_stats
_get_skill_stats = _skill_stats
_get_cost_stats = _cost_stats
_get_recent_tasks = _recent_tasks

__all__ = [
    "AgentStats",
    "CostStats",
    "DailyCost",
    "DashboardResponse",
    "EvaluationStats",
    "RecentTask",
    "SkillAuthorizationByPermission",
    "SkillAuthorizationBySkill",
    "SkillAuthorizationDimension",
    "SkillAuthorizationStats",
    "SkillStats",
    "TaskStats",
    "_agent_stats",
    "_cost_stats",
    "_get_agent_stats",
    "_get_cost_stats",
    "_get_evaluation_stats",
    "_get_recent_tasks",
    "_get_skill_stats",
    "_get_task_stats",
    "_recent_tasks",
    "_skill_stats",
    "_task_stats",
    "router",
]
