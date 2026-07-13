"""Skill permission policy checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_forge.governance import GovernancePolicy
from agent_forge.skills.runtime_spec import normalize_permissions


@dataclass(frozen=True, slots=True)
class StageSkillPolicy:
    key: str
    allowed_permissions: tuple[str, ...]
    allow_unregistered_tools: bool = True
    disabled: bool = False


@dataclass(slots=True)
class SkillToolFilterReport:
    policy_key: str
    input_tool_count: int
    allowed_tool_count: int
    agent_allowed_skill_names: list[str] = field(default_factory=list)
    authorized_skill_names: list[str] = field(default_factory=list)
    authorized_permissions: list[str] = field(default_factory=list)
    authorized_tools: list[dict[str, Any]] = field(default_factory=list)
    excluded_tools: list[dict[str, Any]] = field(default_factory=list)

    def to_context(self) -> dict[str, Any]:
        return {
            "policy_key": self.policy_key,
            "input_tool_count": self.input_tool_count,
            "allowed_tool_count": self.allowed_tool_count,
            "agent_allowed_skill_names": self.agent_allowed_skill_names,
            "authorized_skill_names": self.authorized_skill_names,
            "authorized_permissions": self.authorized_permissions,
            "authorized_tools": self.authorized_tools,
            "excluded_tools": self.excluded_tools,
        }


STAGE_SKILL_POLICIES: dict[str, StageSkillPolicy] = {
    "default": StageSkillPolicy(
        key="default",
        allowed_permissions=("network", "project_context"),
    ),
    "no_tools": StageSkillPolicy(
        key="no_tools",
        allowed_permissions=(),
        allow_unregistered_tools=False,
        disabled=True,
    ),
}


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


def resolve_stage_skill_policy(policy_key: str | None) -> StageSkillPolicy:
    key = (policy_key or "default").strip() or "default"
    return STAGE_SKILL_POLICIES.get(key, STAGE_SKILL_POLICIES["default"])


def filter_tool_defs_for_runtime(
    tool_defs: list[dict],
    *,
    registry: Any | None = None,
    skill_policy_key: str | None = None,
    agent_allowed_skill_names: list[str] | None = None,
    authorized_skill_names: list[str] | None = None,
    authorized_permissions: list[str] | None = None,
) -> tuple[list[dict], SkillToolFilterReport]:
    """Filter LLM-visible tool defs for a pipeline stage and AgentProfile."""
    from agent_forge.skills.registry import get_skill_registry

    skill_registry = registry or get_skill_registry()
    policy = resolve_stage_skill_policy(skill_policy_key)
    allowed_skill_names = _normalize_skill_names(agent_allowed_skill_names)
    allowed_skill_set = set(allowed_skill_names)
    authorized_names = _normalize_skill_names(authorized_skill_names)
    authorized_name_set = set(authorized_names)
    authorized_perms = _normalize_authorized_permissions(authorized_permissions)
    authorized_perm_set = set(authorized_perms)
    filtered: list[dict] = []
    authorized_tools: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for tool_def in tool_defs:
        tool_name = _tool_name(tool_def)
        skill_name = skill_registry.get_skill_name_for_tool(tool_name) if tool_name else None
        runtime_spec = skill_registry.get_runtime_spec(skill_name) if skill_name else None
        permissions = _runtime_permissions(runtime_spec)

        if policy.disabled:
            excluded.append(_excluded_tool(tool_name, skill_name, "policy_disabled", permissions))
            continue

        if allowed_skill_set and (not skill_name or skill_name not in allowed_skill_set):
            excluded.append(_excluded_tool(tool_name, skill_name, "agent_not_allowed", permissions))
            continue

        if runtime_spec is None and not policy.allow_unregistered_tools:
            excluded.append(_excluded_tool(tool_name, skill_name, "unregistered_tool", permissions))
            continue

        denied_permissions = [
            permission
            for permission in permissions
            if permission not in policy.allowed_permissions
        ]
        if denied_permissions:
            skill_authorized = bool(skill_name and skill_name in authorized_name_set)
            permission_authorized = all(
                permission in authorized_perm_set for permission in denied_permissions
            )
            if skill_authorized or permission_authorized:
                filtered.append(tool_def)
                authorized_tools.append(
                    _authorized_tool(
                        tool_name,
                        skill_name,
                        permissions,
                        authorized_by=(
                            "skill_name" if skill_authorized else "permission"
                        ),
                    )
                )
                continue
            excluded.append(_excluded_tool(tool_name, skill_name, "permission_denied", permissions))
            continue

        filtered.append(tool_def)

    return filtered, SkillToolFilterReport(
        policy_key=policy.key,
        input_tool_count=len(tool_defs),
        allowed_tool_count=len(filtered),
        agent_allowed_skill_names=allowed_skill_names,
        authorized_skill_names=authorized_names,
        authorized_permissions=authorized_perms,
        authorized_tools=authorized_tools,
        excluded_tools=excluded,
    )


def _normalize_skill_names(skill_names: list[str] | None) -> list[str]:
    result: list[str] = []
    for skill_name in skill_names or []:
        value = str(skill_name).strip()
        if value and value not in result:
            result.append(value)
    return result


def _tool_name(tool_def: dict) -> str:
    function_def = tool_def.get("function") if isinstance(tool_def, dict) else None
    if not isinstance(function_def, dict):
        return ""
    return str(function_def.get("name") or "").strip()


def _runtime_permissions(runtime_spec: dict[str, Any] | None) -> list[str]:
    try:
        return normalize_permissions(list((runtime_spec or {}).get("permissions") or []))
    except ValueError:
        return ["credential"]


def _normalize_authorized_permissions(permissions: list[str] | None) -> list[str]:
    result: list[str] = []
    for permission in permissions or []:
        try:
            [value] = normalize_permissions([permission])
        except (TypeError, ValueError):
            continue
        if value not in result:
            result.append(value)
    return result


def _excluded_tool(
    tool_name: str,
    skill_name: str | None,
    reason: str,
    permissions: list[str],
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "skill_name": skill_name,
        "reason": reason,
        "permissions": permissions,
    }


def _authorized_tool(
    tool_name: str,
    skill_name: str | None,
    permissions: list[str],
    *,
    authorized_by: str,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "skill_name": skill_name,
        "permissions": permissions,
        "authorized_by": authorized_by,
    }
