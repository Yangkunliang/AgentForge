"""Structured expertise model for an Agent.

This is the concrete vessel for "distilling a developer's capability" into
AgentForge. A senior full-stack developer's tacit knowledge — coding
conventions, code-review checklist, tech-stack preferences, anti-patterns,
debugging heuristics, communication style — is encoded here as structured data
and rendered into the trusted region of the system prompt at stage runtime.

The model is intentionally additive and low-risk: it never overrides platform
rules or the user's explicit request, it only biases the Agent toward the
developer's documented way of working.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

_CONVENTION_LABELS: dict[str, str] = {
    "naming": "命名",
    "formatting": "格式",
    "architecture": "架构",
    "testing": "测试",
}

_TECH_LABELS: dict[str, str] = {
    "frontend": "前端",
    "backend": "后端",
    "database": "数据库",
    "devops": "运维/部署",
    "avoid": "避免使用的",
}


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        return []
    result: list[str] = []
    for item in items:
        if isinstance(item, dict):
            # Accept lightweight {"text": "..."} style entries gracefully.
            text = str(item.get("text") or item.get("value") or "").strip()
        else:
            text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def _as_str_list_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key).strip(): items
        for key, raw in value.items()
        if (items := _as_str_list(raw))
    }


@dataclass
class AgentExpertise:
    """Distilled engineering expertise of a developer, attached to an Agent.

    Every field is optional. Empty fields are omitted from both persistence and
    the rendered prompt so an Agent without distilled expertise behaves exactly
    as before.
    """

    role_title: str = ""
    summary: str = ""
    conventions: dict[str, list[str]] = field(default_factory=dict)
    review_checklist: list[str] = field(default_factory=list)
    tech_preferences: dict[str, list[str]] = field(default_factory=dict)
    anti_patterns: list[str] = field(default_factory=list)
    debugging_heuristics: list[str] = field(default_factory=list)
    communication_style: str = ""

    @classmethod
    def from_dict(cls, data: Any) -> "AgentExpertise":
        if not isinstance(data, dict):
            return cls()
        return cls(
            role_title=str(data.get("role_title") or "").strip(),
            summary=str(data.get("summary") or "").strip(),
            conventions=_as_str_list_map(data.get("conventions")),
            review_checklist=_as_str_list(data.get("review_checklist")),
            tech_preferences=_as_str_list_map(data.get("tech_preferences")),
            anti_patterns=_as_str_list(data.get("anti_patterns")),
            debugging_heuristics=_as_str_list(data.get("debugging_heuristics")),
            communication_style=str(data.get("communication_style") or "").strip(),
        )

    def to_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value}

    def is_empty(self) -> bool:
        return not self.to_dict()

    def to_prompt_section(self) -> str:
        """Render the expertise as a compact, trusted system-prompt section."""
        if self.is_empty():
            return ""

        lines = [
            "**专家工作标准（来自 Agent 配置，代表该开发者的个人工程偏好）**："
        ]
        if self.role_title:
            lines.append(f"- 角色定位：{self.role_title}")
        if self.summary:
            lines.append(f"- 简介：{self.summary}")

        if self.conventions:
            lines.append("- 编码规范：")
            for key, items in self.conventions.items():
                label = _CONVENTION_LABELS.get(key, key)
                lines.append(f"  - {label}：{'; '.join(items)}")

        if self.review_checklist:
            lines.append("- 代码审查必查项：")
            for item in self.review_checklist[:20]:
                lines.append(f"  - {item}")

        if self.tech_preferences:
            lines.append("- 技术栈偏好：")
            for key, items in self.tech_preferences.items():
                label = _TECH_LABELS.get(key, key)
                lines.append(f"  - {label}：{', '.join(items)}")

        if self.anti_patterns:
            lines.append("- 反模式 / 雷区（务必避免）：")
            for item in self.anti_patterns[:20]:
                lines.append(f"  - {item}")

        if self.debugging_heuristics:
            lines.append("- 调试套路：")
            for item in self.debugging_heuristics[:20]:
                lines.append(f"  - {item}")

        if self.communication_style:
            lines.append(f"- 输出风格：{self.communication_style}")

        lines.append(
            "- 以上标准应作为你工作的默认准则；当用户明确要求其他方式时，以用户要求为准，"
            "但需指出与既定标准的偏差。"
        )
        return "\n".join(lines)
