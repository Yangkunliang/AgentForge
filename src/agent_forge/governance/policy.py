"""Unified policy decisions for confirmation and high-risk actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DecisionValue = Literal["allow", "require_confirmation", "deny"]
HIGH_RISK_SKILL_PERMISSIONS = {"filesystem", "shell", "credential"}


@dataclass(slots=True)
class GovernanceDecision:
    decision: DecisionValue
    reason: str
    risk_level: str = "low"
    confirmation_type: str | None = None
    reason_code: str | None = None
    impact_scope: list[dict[str, str]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"

    def audit_payload(self) -> dict:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "reason_code": self.reason_code,
            "risk_level": self.risk_level,
            "confirmation_type": self.confirmation_type,
            "impact_scope": self.impact_scope,
            **self.metadata,
        }


class GovernancePolicy:
    """Policy entrypoint shared by Pipeline, Skill, and Delivery flows."""

    _STAGE_GATE_REASONS = {
        "prd_review": ("需求确认", "需求/PRD 是后续阶段的基础，继续前需要用户确认范围和验收标准。"),
        "architecture_review": ("技术选型确认", "架构和技术选型会显著影响后续工作量，继续前需要用户确认。"),
        "diff_review": ("需求 Diff 确认", "迭代差异会决定实际改动范围，继续前需要用户确认。"),
        "impact_review": ("影响范围确认", "本阶段涉及影响范围和回归面，继续前需要用户确认。"),
        "prototype_review": ("原型确认", "UI 原型会影响后续视觉实现，继续前需要用户确认。"),
    }

    def evaluate_stage_confirmation(
        self,
        *,
        stage_id: str,
        stage_name: str,
        confirmation_gate: str | None,
    ) -> GovernanceDecision:
        if not confirmation_gate:
            return GovernanceDecision(
                decision="allow",
                reason="该阶段不需要人工确认。",
                impact_scope=[_scope("pipeline_stage", stage_id, stage_name)],
            )

        label, reason = self._STAGE_GATE_REASONS.get(
            confirmation_gate,
            ("阶段确认", "该阶段产物会影响后续执行，继续前需要用户确认。"),
        )
        return GovernanceDecision(
            decision="require_confirmation",
            reason=reason,
            risk_level="medium",
            confirmation_type=confirmation_gate,
            reason_code=confirmation_gate,
            impact_scope=[_scope("pipeline_stage", stage_id, stage_name)],
            metadata={"label": label},
        )

    def evaluate_delivery_confirmation(
        self,
        *,
        channel: str,
        target_path: str,
        artifact_id: str,
        mount_id: str | None = None,
        confirmed: bool,
    ) -> GovernanceDecision:
        impact_scope = [_scope("artifact", artifact_id, artifact_id)]
        if mount_id:
            impact_scope.append(_scope("mount", mount_id, mount_id))
        impact_scope.append(_scope("path", target_path, target_path))

        confirmation_type = {
            "github": "delivery_pr",
            "zip": "delivery_package",
        }.get(channel, "delivery_write")
        if confirmed:
            return GovernanceDecision(
                decision="allow",
                reason="用户已确认交付动作。",
                risk_level="high",
                confirmation_type=confirmation_type,
                impact_scope=impact_scope,
                metadata={"channel": channel},
            )

        return GovernanceDecision(
            decision="require_confirmation",
            reason="写回、创建 PR 或生成交付包前需要用户确认影响范围。",
            risk_level="high",
            confirmation_type=confirmation_type,
            reason_code="missing_confirmation",
            impact_scope=impact_scope,
            metadata={"channel": channel},
        )

    def evaluate_skill_call(
        self,
        *,
        skill_name: str | None,
        tool_name: str,
        permissions: list[str],
        confirmed: bool = False,
    ) -> GovernanceDecision:
        normalized = _normalize_permission_labels(permissions)
        high_risk = [permission for permission in normalized if permission in HIGH_RISK_SKILL_PERMISSIONS]
        impact_scope = [
            _scope("skill", skill_name or tool_name, skill_name or tool_name),
            _scope("tool", tool_name, tool_name),
        ]
        if not high_risk:
            return GovernanceDecision(
                decision="allow",
                reason="Skill 权限在默认允许范围内。",
                impact_scope=impact_scope,
                metadata={"permissions": normalized},
            )
        if confirmed:
            return GovernanceDecision(
                decision="allow",
                reason="用户已确认高风险 Skill 调用。",
                risk_level="high",
                confirmation_type="skill_high_risk",
                impact_scope=impact_scope,
                metadata={"permissions": normalized},
            )
        return GovernanceDecision(
            decision="require_confirmation",
            reason="该 Skill 声明了高风险权限，调用前需要用户确认。",
            risk_level="high",
            confirmation_type="skill_high_risk",
            reason_code="high_risk_permission",
            impact_scope=impact_scope,
            metadata={"permissions": normalized, "high_risk_permissions": high_risk},
        )


def _scope(scope_type: str, scope_id: str, label: str) -> dict[str, str]:
    return {"type": scope_type, "id": scope_id, "label": label}


def _normalize_permission_labels(permissions: list[str]) -> list[str]:
    result: list[str] = []
    for permission in permissions:
        value = str(permission).strip()
        if value and value not in result:
            result.append(value)
    return result
