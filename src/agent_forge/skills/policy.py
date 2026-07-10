"""Skill permission policy checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_forge.governance import GovernancePolicy
from agent_forge.skills.runtime_spec import normalize_permissions


@dataclass(slots=True)
class SkillPolicyDecision:
    allowed: bool
    denied_permissions: list[str] = field(default_factory=list)
    reason: str | None = None
    governance_decision: dict | None = None


@dataclass(slots=True)
class SkillPermissionPolicy:
    allowed_permissions: list[str] = field(default_factory=lambda: ["network", "project_context"])

    def evaluate(
        self,
        required_permissions: list[str],
        *,
        skill_name: str | None = None,
        tool_name: str = "",
    ) -> SkillPolicyDecision:
        required = normalize_permissions(required_permissions)
        governance_decision = GovernancePolicy().evaluate_skill_call(
            skill_name=skill_name,
            tool_name=tool_name or skill_name or "unknown_tool",
            permissions=required,
            confirmed=False,
        )
        if governance_decision.decision == "require_confirmation":
            return SkillPolicyDecision(
                allowed=False,
                denied_permissions=governance_decision.metadata.get("high_risk_permissions", []),
                reason=governance_decision.reason,
                governance_decision=governance_decision.audit_payload(),
            )

        allowed = set(normalize_permissions(self.allowed_permissions))
        denied = [permission for permission in required if permission not in allowed]
        if denied:
            return SkillPolicyDecision(
                allowed=False,
                denied_permissions=denied,
                reason=f"Skill permissions not allowed: {', '.join(denied)}",
                governance_decision=governance_decision.audit_payload(),
            )
        return SkillPolicyDecision(allowed=True)


DEFAULT_SKILL_PERMISSION_POLICY = SkillPermissionPolicy()
