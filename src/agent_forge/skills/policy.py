"""Skill permission policy checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_forge.skills.runtime_spec import normalize_permissions


@dataclass(slots=True)
class SkillPolicyDecision:
    allowed: bool
    denied_permissions: list[str] = field(default_factory=list)
    reason: str | None = None


@dataclass(slots=True)
class SkillPermissionPolicy:
    allowed_permissions: list[str] = field(default_factory=lambda: ["network", "project_context"])

    def evaluate(self, required_permissions: list[str]) -> SkillPolicyDecision:
        required = normalize_permissions(required_permissions)
        allowed = set(normalize_permissions(self.allowed_permissions))
        denied = [permission for permission in required if permission not in allowed]
        if denied:
            return SkillPolicyDecision(
                allowed=False,
                denied_permissions=denied,
                reason=f"Skill permissions not allowed: {', '.join(denied)}",
            )
        return SkillPolicyDecision(allowed=True)


DEFAULT_SKILL_PERMISSION_POLICY = SkillPermissionPolicy()
