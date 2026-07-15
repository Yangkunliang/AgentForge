"""Pipeline stage catalog.

This module is the backend source of truth for intent -> stage definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

from fastapi import HTTPException

IntentType = Literal["new_feature", "iteration", "ui_adjust", "bug_fix"]
ArtifactType = Literal["prd", "architecture", "api_spec", "code", "test", "report", "diff"]
ARTIFACT_TYPES = frozenset(get_args(ArtifactType))


@dataclass(frozen=True)
class QuickAction:
    id: str
    label: str
    prompt: str
    highlighted: bool = False


@dataclass(frozen=True)
class StageDefinition:
    stage_id: str
    stage_name: str
    description: str = ""
    required: bool = True
    confirmation_required: bool = False
    confirmation_gate: str | None = None
    required_input_artifact_types: tuple[str, ...] = ()
    output_artifact_types: tuple[str, ...] = ("report",)
    success_criteria: tuple[str, ...] = ()
    default_agent_selector: str = "planner"
    model_route_key: str = "default"
    skill_policy_key: str = "default"

    @property
    def can_skip(self) -> bool:
        return not self.required

    @property
    def can_restore(self) -> bool:
        return not self.required


@dataclass(frozen=True)
class IntentPipelineDefinition:
    intent_type: IntentType
    label: str
    description: str
    placeholder: str
    stages: tuple[StageDefinition, ...]
    default_actions: tuple[QuickAction, ...]


PIPELINE_CATALOG: dict[IntentType, IntentPipelineDefinition] = {
    "new_feature": IntentPipelineDefinition(
        intent_type="new_feature",
        label="全新功能",
        description="新实体、新表、新路由或跨模块改动，适合完整开发流水线。",
        placeholder="描述你的新功能需求，例如：添加用户权限管理模块...",
        stages=(
            StageDefinition(
                "analysis",
                "需求分析",
                "明确用户目标、范围、验收标准和非目标。",
                confirmation_required=True,
                confirmation_gate="prd_review",
                output_artifact_types=("prd",),
                success_criteria=(
                    "明确用户目标与角色。",
                    "列出范围、非目标和验收标准。",
                ),
                default_agent_selector="planner",
            ),
            StageDefinition(
                "design",
                "架构设计",
                "明确模块边界、数据流、接口和关键技术取舍。",
                confirmation_required=True,
                confirmation_gate="architecture_review",
                required_input_artifact_types=("prd",),
                output_artifact_types=("architecture",),
                success_criteria=(
                    "定义模块边界和数据流。",
                    "说明接口、技术取舍和风险。",
                ),
                default_agent_selector="planner",
            ),
            StageDefinition(
                "db_api",
                "DB & API",
                "设计数据结构、迁移、服务接口和错误处理。",
                required_input_artifact_types=("prd", "architecture"),
                output_artifact_types=("api_spec",),
                success_criteria=(
                    "定义数据模型与迁移。",
                    "定义 API 契约、错误和权限。",
                ),
                default_agent_selector="coder",
            ),
            StageDefinition(
                "task_split",
                "任务拆解",
                "把需求拆成可执行、可验证、可提交的小任务。",
                required_input_artifact_types=("prd", "architecture", "api_spec"),
                output_artifact_types=("report",),
                success_criteria=(
                    "拆成可独立验证和提交的任务。",
                    "声明依赖、文件范围和测试命令。",
                ),
                default_agent_selector="planner",
            ),
            StageDefinition(
                "ui_prototype",
                "UI 原型",
                "产出页面结构、交互状态和视觉验收点。",
                required=False,
                required_input_artifact_types=("prd",),
                output_artifact_types=("prd",),
                success_criteria=(
                    "覆盖页面结构、关键状态和响应式。",
                    "给出视觉验收点。",
                ),
                default_agent_selector="designer",
            ),
            StageDefinition(
                "backend_dev",
                "后端开发",
                "实现后端模型、服务、路由、迁移和后端测试。",
                required_input_artifact_types=("prd", "architecture", "api_spec", "report"),
                output_artifact_types=("code",),
                success_criteria=(
                    "实现后端与自动化测试。",
                    "说明改动文件和回归结果。",
                ),
                default_agent_selector="coder",
            ),
            StageDefinition(
                "frontend_dev",
                "前端开发",
                "实现前端状态、接口、页面交互和构建校验。",
                required=False,
                required_input_artifact_types=("prd", "api_spec", "report"),
                output_artifact_types=("code",),
                success_criteria=(
                    "实现前端交互与错误状态。",
                    "构建通过并说明视觉验收。",
                ),
                default_agent_selector="coder",
            ),
            StageDefinition(
                "testing",
                "测试交付",
                "执行回归、整理验证结果和交付说明。",
                required_input_artifact_types=("prd", "code"),
                output_artifact_types=("test",),
                success_criteria=(
                    "执行目标与相关回归。",
                    "记录命令、结果、失败和残余风险。",
                ),
                default_agent_selector="tester",
            ),
        ),
        default_actions=(
            QuickAction("define_scope", "定义需求范围", "帮我梳理这个新功能的需求范围和验收标准。", True),
            QuickAction("tech_design", "技术方案设计", "帮我设计这个功能的技术方案，包括架构图和关键类设计。"),
            QuickAction("api_design", "API 接口设计", "帮我设计这个功能的 RESTful API 接口规范。"),
            QuickAction("estimate", "工作量评估", "帮我评估实现这个功能所需的时间和资源。"),
        ),
    ),
    "iteration": IntentPipelineDefinition(
        intent_type="iteration",
        label="迭代优化",
        description="改现有逻辑、范围局部、不新增核心实体时使用。",
        placeholder="描述你的迭代需求，例如：优化订单列表加载性能...",
        stages=(
            StageDefinition(
                "diff",
                "需求 Diff",
                "描述本次变化和旧行为差异。",
                confirmation_required=True,
                confirmation_gate="diff_review",
                output_artifact_types=("diff",),
                success_criteria=(
                    "描述旧行为、新行为和不变范围。",
                    "给出验收差异。",
                ),
                default_agent_selector="planner",
            ),
            StageDefinition(
                "impact",
                "影响评估",
                "评估受影响模块、文件、接口和回归范围。",
                required=False,
                confirmation_required=True,
                confirmation_gate="impact_review",
                required_input_artifact_types=("diff",),
                output_artifact_types=("report",),
                success_criteria=(
                    "列出受影响模块、文件和 API。",
                    "定义回归范围和风险。",
                ),
                default_agent_selector="reviewer",
            ),
            StageDefinition(
                "backend_dev",
                "后端开发",
                "实现后端局部改动和测试。",
                required_input_artifact_types=("diff",),
                output_artifact_types=("code",),
                success_criteria=(
                    "实现最小后端改动与测试。",
                    "保持无关行为不变。",
                ),
                default_agent_selector="coder",
            ),
            StageDefinition(
                "frontend_dev",
                "前端开发",
                "实现必要前端改动和构建校验。",
                required=False,
                required_input_artifact_types=("diff",),
                output_artifact_types=("code",),
                success_criteria=(
                    "实现必要前端改动与状态。",
                    "构建结果可复核。",
                ),
                default_agent_selector="coder",
            ),
            StageDefinition(
                "regression",
                "回归测试",
                "执行目标回归并整理验证结论。",
                required_input_artifact_types=("diff", "code"),
                output_artifact_types=("test",),
                success_criteria=(
                    "执行变更点和相关回归。",
                    "记录失败与残余风险。",
                ),
                default_agent_selector="tester",
            ),
        ),
        default_actions=(
            QuickAction("analyze_diff", "分析需求变更", "帮我分析这次需求变更的具体内容和影响范围。", True),
            QuickAction("code_review", "代码审查", "帮我审查这次变更涉及的代码，确保质量。"),
            QuickAction("risk_assess", "风险评估", "帮我评估这次迭代可能带来的风险和应对措施。"),
        ),
    ),
    "ui_adjust": IntentPipelineDefinition(
        intent_type="ui_adjust",
        label="UI 调整",
        description="只改前端文件、不动接口和数据库时使用。",
        placeholder="描述你的 UI 调整需求，例如：修改首页布局，增加暗色模式...",
        stages=(
            StageDefinition(
                "prototype_diff",
                "原型 Diff",
                "明确视觉、布局、交互和状态差异。",
                confirmation_required=True,
                confirmation_gate="prototype_review",
                output_artifact_types=("diff",),
                success_criteria=(
                    "明确布局、视觉和交互差异。",
                    "列出响应式和状态验收点。",
                ),
                default_agent_selector="designer",
            ),
            StageDefinition(
                "frontend_dev",
                "前端开发",
                "实现前端组件、样式和交互。",
                required_input_artifact_types=("diff",),
                output_artifact_types=("code",),
                success_criteria=(
                    "实现组件、样式和交互。",
                    "覆盖加载、空、错和禁用状态。",
                ),
                default_agent_selector="coder",
            ),
            StageDefinition(
                "visual",
                "视觉验收",
                "检查响应式、溢出、状态和视觉一致性。",
                required_input_artifact_types=("diff", "code"),
                output_artifact_types=("report",),
                success_criteria=(
                    "检查响应式、溢出和一致性。",
                    "记录视觉验收结论。",
                ),
                default_agent_selector="reviewer",
            ),
        ),
        default_actions=(
            QuickAction("design_spec", "设计规范", "帮我制定这个 UI 调整的设计规范和交互细节。", True),
            QuickAction("component_build", "组件开发", "帮我实现这个 UI 组件，包括响应式适配。"),
            QuickAction("style_refine", "样式优化", "帮我优化这个页面的样式和视觉效果。"),
        ),
    ),
    "bug_fix": IntentPipelineDefinition(
        intent_type="bug_fix",
        label="Bug 修复",
        description="明确报错、性能问题或代码坏味道时使用。",
        placeholder="描述你的 Bug 或重构需求，例如：修复登录页面输入框验证问题...",
        stages=(
            StageDefinition(
                "locate",
                "问题定位",
                "定位问题现象、复现条件和根因假设。",
                output_artifact_types=("report",),
                success_criteria=(
                    "给出可复现现象和根因证据。",
                    "区分事实与假设。",
                ),
                default_agent_selector="researcher",
            ),
            StageDefinition(
                "impact_scope",
                "影响范围分析",
                "评估修复影响面、风险和回归范围。",
                confirmation_required=True,
                confirmation_gate="impact_review",
                required_input_artifact_types=("report",),
                output_artifact_types=("report",),
                success_criteria=(
                    "列出受影响路径和风险。",
                    "定义最小修复与回归范围。",
                ),
                default_agent_selector="reviewer",
            ),
            StageDefinition(
                "fix",
                "修复",
                "实现最小修复并保留回归测试。",
                required_input_artifact_types=("report",),
                output_artifact_types=("code",),
                success_criteria=(
                    "实现最小修复和回归测试。",
                    "不扩大无关改动。",
                ),
                default_agent_selector="coder",
            ),
            StageDefinition(
                "regression",
                "回归测试",
                "执行复现用例和相关回归。",
                required_input_artifact_types=("report", "code"),
                output_artifact_types=("test",),
                success_criteria=(
                    "复现用例转绿。",
                    "相关回归通过并记录残余风险。",
                ),
                default_agent_selector="tester",
            ),
        ),
        default_actions=(
            QuickAction("debug_log", "日志分析", "帮我分析这段错误日志，找出问题根源。", True),
            QuickAction("reproduce", "复现步骤", "帮我梳理这个 Bug 的复现步骤和条件。"),
            QuickAction("fix_verify", "修复验证", "帮我验证这个修复是否正确，有无遗漏。"),
        ),
    ),
}


def normalize_intent(intent_type: str | None) -> IntentType:
    if intent_type in PIPELINE_CATALOG:
        return intent_type  # type: ignore[return-value]
    return "iteration"


def list_pipeline_definitions() -> list[IntentPipelineDefinition]:
    return list(PIPELINE_CATALOG.values())


def get_pipeline_definition(intent_type: str) -> IntentPipelineDefinition:
    if intent_type not in PIPELINE_CATALOG:
        raise HTTPException(status_code=404, detail="Pipeline catalog not found")
    return PIPELINE_CATALOG[intent_type]  # type: ignore[index]


def get_stage_definitions_for_intent(intent_type: str | None) -> tuple[StageDefinition, ...]:
    return PIPELINE_CATALOG[normalize_intent(intent_type)].stages


def get_stage_definition(intent_type: str | None, stage_id: str) -> StageDefinition | None:
    for stage in get_stage_definitions_for_intent(intent_type):
        if stage.stage_id == stage_id:
            return stage
    return None


def quick_action_to_dict(action: QuickAction) -> dict:
    return {
        "id": action.id,
        "label": action.label,
        "prompt": action.prompt,
        "highlighted": action.highlighted,
    }


def stage_definition_to_dict(stage: StageDefinition, order_index: int) -> dict:
    return {
        "stage_id": stage.stage_id,
        "stage_name": stage.stage_name,
        "description": stage.description,
        "order_index": order_index,
        "required": stage.required,
        "confirmation_required": stage.confirmation_required,
        "confirmation_policy": {
            "required": stage.confirmation_required,
            "type": "stage_output" if stage.confirmation_required else "none",
            "gate": stage.confirmation_gate,
        },
        "required_input_artifact_types": list(stage.required_input_artifact_types),
        "output_artifact_types": list(stage.output_artifact_types),
        "success_criteria": list(stage.success_criteria),
        "default_agent_selector": stage.default_agent_selector,
        "model_route_key": stage.model_route_key,
        "skill_policy_key": stage.skill_policy_key,
        "can_skip": stage.can_skip,
        "can_restore": stage.can_restore,
    }


def pipeline_definition_to_dict(definition: IntentPipelineDefinition) -> dict:
    return {
        "intent_type": definition.intent_type,
        "label": definition.label,
        "description": definition.description,
        "placeholder": definition.placeholder,
        "stages": [
            stage_definition_to_dict(stage, index)
            for index, stage in enumerate(definition.stages)
        ],
        "default_actions": [
            quick_action_to_dict(action)
            for action in definition.default_actions
        ],
    }
