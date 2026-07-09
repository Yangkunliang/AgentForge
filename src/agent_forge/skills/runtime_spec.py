"""Runtime contract for installable Skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ALLOWED_SKILL_PERMISSIONS = {
    "network",
    "filesystem",
    "shell",
    "credential",
    "project_context",
}
HIGH_RISK_PERMISSIONS = {"filesystem", "shell", "credential"}
MEDIUM_RISK_PERMISSIONS = {"network", "project_context"}


def normalize_permissions(permissions: list[str] | None) -> list[str]:
    result: list[str] = []
    for permission in permissions or []:
        value = str(permission).strip()
        if not value:
            continue
        if value not in ALLOWED_SKILL_PERMISSIONS:
            raise ValueError(f"Unknown skill permission: {value}")
        if value not in result:
            result.append(value)
    return result


def classify_permission_risk(permissions: list[str]) -> str:
    permission_set = set(permissions)
    if permission_set & HIGH_RISK_PERMISSIONS:
        return "high"
    if permission_set & MEDIUM_RISK_PERMISSIONS:
        return "medium"
    return "low"


@dataclass(slots=True)
class SkillRuntimeSpec:
    name: str
    version: str
    source_type: str
    manifest_hash: str
    tool_defs: list[dict[str, Any]]
    permissions: list[str] = field(default_factory=list)
    executor_kind: str = "python"
    executor_entry_point: str | None = None
    enabled: bool = True
    audit_level: str = "standard"
    source: str | None = None

    @property
    def risk_level(self) -> str:
        return classify_permission_risk(self.permissions)

    @property
    def requires_confirmation(self) -> bool:
        return self.risk_level == "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "source_type": self.source_type,
            "manifest_hash": self.manifest_hash,
            "tool_defs": self.tool_defs,
            "permissions": self.permissions,
            "executor_kind": self.executor_kind,
            "executor_entry_point": self.executor_entry_point,
            "enabled": self.enabled,
            "audit_level": self.audit_level,
            "source": self.source,
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
        }


@dataclass(slots=True)
class SkillImportPreview:
    name: str
    version: str
    description: str
    source: str
    source_type: str
    manifest_hash: str
    permissions: list[str]
    tools: list[dict[str, Any]]
    tool_defs: list[dict[str, Any]]
    executor_kind: str
    executor_entry_point: str | None
    audit_level: str
    runtime_spec: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    @property
    def risk_level(self) -> str:
        return classify_permission_risk(self.permissions)

    @property
    def requires_confirmation(self) -> bool:
        return self.risk_level == "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "source": self.source,
            "source_type": self.source_type,
            "manifest_hash": self.manifest_hash,
            "permissions": self.permissions,
            "tools": self.tools,
            "tool_defs": self.tool_defs,
            "executor_kind": self.executor_kind,
            "executor_entry_point": self.executor_entry_point,
            "audit_level": self.audit_level,
            "runtime_spec": self.runtime_spec,
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
            "warnings": self.warnings,
        }
