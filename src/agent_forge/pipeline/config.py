"""Intent to pipeline stage configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IntentType = Literal["new_feature", "iteration", "ui_adjust", "bug_fix"]


@dataclass(frozen=True)
class StageConfig:
    stage_id: str
    stage_name: str
    required: bool = True
    confirmation_required: bool = False


PIPELINE_CONFIGS: dict[IntentType, list[StageConfig]] = {
    "new_feature": [
        StageConfig("analysis", "需求分析", confirmation_required=True),
        StageConfig("design", "架构设计", confirmation_required=True),
        StageConfig("db_api", "DB & API"),
        StageConfig("task_split", "任务拆解"),
        StageConfig("ui_prototype", "UI 原型", required=False),
        StageConfig("backend_dev", "后端开发"),
        StageConfig("frontend_dev", "前端开发", required=False),
        StageConfig("testing", "测试交付"),
    ],
    "iteration": [
        StageConfig("diff", "需求 Diff", confirmation_required=True),
        StageConfig("impact", "影响评估", required=False, confirmation_required=True),
        StageConfig("backend_dev", "后端开发"),
        StageConfig("frontend_dev", "前端开发", required=False),
        StageConfig("regression", "回归测试"),
    ],
    "ui_adjust": [
        StageConfig("prototype_diff", "原型 Diff", confirmation_required=True),
        StageConfig("frontend_dev", "前端开发"),
        StageConfig("visual", "视觉验收"),
    ],
    "bug_fix": [
        StageConfig("locate", "问题定位"),
        StageConfig("impact_scope", "影响范围分析", confirmation_required=True),
        StageConfig("fix", "修复"),
        StageConfig("regression", "回归测试"),
    ],
}


def normalize_intent(intent_type: str | None) -> IntentType:
    if intent_type in PIPELINE_CONFIGS:
        return intent_type  # type: ignore[return-value]
    return "iteration"

