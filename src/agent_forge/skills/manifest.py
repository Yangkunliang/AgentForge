"""Skill Manifest 解析器

解析 skill.md 文件，提取 frontmatter 元数据和工具定义，
并将 manifest 转换为 OpenAI tools format 供 LLM tool_use 使用。
"""

from __future__ import annotations

import logging
import re
import hashlib
from typing import Any
from pathlib import Path

import yaml

from agent_forge.skills.runtime_spec import (
    SkillImportPreview,
    SkillRuntimeSpec,
    normalize_permissions,
)

logger = logging.getLogger(__name__)


class SkillManifestError(ValueError):
    """Raised when an installable Skill manifest is missing or invalid."""


def parse_skill_md(content: str) -> dict[str, Any]:
    """解析 skill.md 文件，提取 frontmatter YAML 和正文。

    支持标准 YAML frontmatter：
    ---
    name: my-skill
    version: 1.0.0
    description: What this skill does
    ---

    # Skill body...

    Returns:
        {
            "name": "my-skill",
            "version": "1.0.0",
            "description": "...",
            "body": "# Skill body...",
            "raw_frontmatter": {...},
        }
    """
    result: dict[str, Any] = {"body": content, "raw_frontmatter": {}}

    # 匹配 YAML frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if not match:
        logger.debug("No frontmatter found in skill.md")
        result["body"] = content
        return result

    raw = match.group(1)
    result["body"] = match.group(2) or ""

    # 简单 YAML 解析（不需要完整 YAML 库，只解析 key: value）
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        colon_idx = line.find(":")
        if colon_idx < 0:
            continue
        key = line[:colon_idx].strip()
        value = line[colon_idx + 1:].strip().strip('"').strip("'")
        # 尝试转换为数字
        if value.isdigit():
            value = int(value)
        result["raw_frontmatter"][key] = value
        # 快捷访问常用字段
        result[key] = value

    return result


def to_tool_def(manifest: dict[str, Any]) -> list[dict]:
    """将 Skill 的 manifest 数据转为 OpenAI tools format 定义列表。

    Skill manifest 中 tool 字段格式：
    {
        "tool": {
            "name": "web_search",
            "description": "...",
            "parameters": {
                "query": {"type": "string", "description": "..."},
                "max_results": {"type": "integer", "description": "...", "default": 5},
            }
        }
    }

    转换为 OpenAI tools format:
    [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "..."},
                        "max_results": {"type": "integer", "description": "...", "default": 5},
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    """
    tool_defs: list[dict] = []

    tool_spec = manifest.get("tool")
    if not tool_spec:
        return tool_defs

    # 从 parameters 中推断 required 字段
    parameters = tool_spec.get("parameters", {})
    required_keys = [
        k for k, v in parameters.items()
        if v.get("type") == "string" and "default" not in v
    ]

    tool_def: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": tool_spec["name"],
            "description": tool_spec.get("description", ""),
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required_keys,
            },
        },
    }
    tool_defs.append(tool_def)

    # 支持多个 tools（某些 skill 可能定义多个工具）
    for extra_tool in tool_spec.get("tools", []):
        extra_params = extra_tool.get("parameters", {})
        extra_required = [
            k for k, v in extra_params.items()
            if v.get("type") == "string" and "default" not in v
        ]
        tool_defs.append({
            "type": "function",
            "function": {
                "name": extra_tool["name"],
                "description": extra_tool.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": extra_params,
                    "required": extra_required,
                },
            },
        })

    return tool_defs


def load_skill_manifest(
    skill_dir: str | Path,
    source: str = "local",
    source_type: str = "local",
) -> SkillImportPreview:
    """Load and validate an installable Skill manifest from a directory.

    Preferred format is `agentforge-skill.yaml`. The legacy `skill.md`
    frontmatter/tool block remains accepted as a compatibility fallback.
    """
    path = Path(skill_dir)
    if not path.is_dir():
        raise SkillManifestError(f"Skill source is not a directory: {path}")

    manifest_path = path / "agentforge-skill.yaml"
    if manifest_path.exists():
        raw_text = manifest_path.read_text(encoding="utf-8")
        try:
            raw_manifest = yaml.safe_load(raw_text) or {}
        except yaml.YAMLError as exc:
            raise SkillManifestError(f"agentforge-skill.yaml is invalid YAML: {exc}") from exc
        if not isinstance(raw_manifest, dict):
            raise SkillManifestError("agentforge-skill.yaml must contain an object")
        return _preview_from_manifest(raw_manifest, raw_text, source=source, source_type=source_type)

    skill_md = path / "skill.md"
    if skill_md.exists():
        raw_text = skill_md.read_text(encoding="utf-8")
        parsed = parse_skill_md(raw_text)
        manifest = _compat_manifest_from_skill_md(parsed, path.name)
        return _preview_from_manifest(manifest, raw_text, source=source, source_type=source_type)

    raise SkillManifestError("Skill manifest not found: expected agentforge-skill.yaml or skill.md")


def _preview_from_manifest(
    raw_manifest: dict[str, Any],
    raw_text: str,
    *,
    source: str,
    source_type: str,
) -> SkillImportPreview:
    name = str(raw_manifest.get("name") or "").strip()
    if not name:
        raise SkillManifestError("Skill manifest field 'name' is required")
    version = str(raw_manifest.get("version") or "1.0.0")
    description = str(raw_manifest.get("description") or "")

    try:
        permissions = normalize_permissions(list(raw_manifest.get("permissions") or []))
    except ValueError as exc:
        raise SkillManifestError(str(exc)) from exc

    executor = raw_manifest.get("executor") or {}
    if not isinstance(executor, dict):
        raise SkillManifestError("Skill manifest field 'executor' must be an object")
    executor_kind = str(executor.get("kind") or "python")
    executor_entry_point = executor.get("entry_point")
    if executor_entry_point is not None:
        executor_entry_point = str(executor_entry_point)

    audit = raw_manifest.get("audit") or {}
    if not isinstance(audit, dict):
        raise SkillManifestError("Skill manifest field 'audit' must be an object")
    audit_level = str(audit.get("level") or "standard")

    tools = _normalize_tools(raw_manifest)
    if not tools:
        raise SkillManifestError("Skill manifest must declare at least one tool")
    tool_defs = [_to_openai_tool_def(tool) for tool in tools]

    manifest_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    runtime_spec = SkillRuntimeSpec(
        name=name,
        version=version,
        source_type=source_type,
        manifest_hash=manifest_hash,
        tool_defs=tool_defs,
        permissions=permissions,
        executor_kind=executor_kind,
        executor_entry_point=executor_entry_point,
        audit_level=audit_level,
        source=source,
    ).to_dict()

    return SkillImportPreview(
        name=name,
        version=version,
        description=description,
        source=source,
        source_type=source_type,
        manifest_hash=manifest_hash,
        permissions=permissions,
        tools=tools,
        tool_defs=tool_defs,
        executor_kind=executor_kind,
        executor_entry_point=executor_entry_point,
        audit_level=audit_level,
        runtime_spec=runtime_spec,
    )


def _compat_manifest_from_skill_md(parsed: dict[str, Any], fallback_name: str) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "name": parsed.get("name") or fallback_name,
        "version": parsed.get("version") or "1.0.0",
        "description": parsed.get("description") or "",
        "permissions": parsed.get("permissions") or [],
    }
    tool_spec = parsed.get("tool")
    if not tool_spec:
        body = parsed.get("body", "")
        tool_match = re.search(r"##\s*Tool Definition\s*\n```yaml\s*\n(.*?)```", body, re.DOTALL)
        if tool_match:
            try:
                tool_spec = yaml.safe_load(tool_match.group(1)) or {}
            except yaml.YAMLError as exc:
                raise SkillManifestError(f"skill.md tool definition is invalid YAML: {exc}") from exc
    if tool_spec:
        manifest["tools"] = [tool_spec]
    return manifest


def _normalize_tools(raw_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw_tools = raw_manifest.get("tools")
    if raw_tools is None and raw_manifest.get("tool"):
        raw_tools = [raw_manifest["tool"]]
    if not isinstance(raw_tools, list):
        raise SkillManifestError("Skill manifest field 'tools' must be a list")

    tools: list[dict[str, Any]] = []
    for raw_tool in raw_tools:
        if not isinstance(raw_tool, dict):
            raise SkillManifestError("Each Skill tool must be an object")
        tool = raw_tool.get("function") if raw_tool.get("type") == "function" else raw_tool
        if not isinstance(tool, dict):
            raise SkillManifestError("Each Skill tool function must be an object")
        name = str(tool.get("name") or "").strip()
        if not name:
            raise SkillManifestError("Each Skill tool requires a name")
        parameters = tool.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise SkillManifestError("Each Skill tool parameters must be an object")
        tools.append(
            {
                "name": name,
                "description": str(tool.get("description") or ""),
                "parameters": parameters,
            }
        )
    return tools


def _to_openai_tool_def(tool: dict[str, Any]) -> dict[str, Any]:
    parameters = tool.get("parameters") or {}
    required = [
        key
        for key, value in parameters.items()
        if isinstance(value, dict) and value.get("type") == "string" and "default" not in value
    ]
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }


def generate_skill_md(skill_name: str, description: str, tool_spec: dict = None) -> str:
    """从 Skill 元数据反向生成 skill.md 文件内容。

    用于导出已注册的 Skill 为可分发格式。
    """
    frontmatter = (
        f"---\n"
        f"name: {skill_name}\n"
        f"version: 1.0.0\n"
        f"description: {description}\n"
        f"---\n"
    )

    body = f"# {skill_name}\n\n{description}\n\n"

    if tool_spec:
        body += "## Tool Definition\n\n"
        body += "```yaml\n"
        # 简单 YAML 序列化
        for key, value in tool_spec.items():
            if isinstance(value, dict):
                body += f"{key}:\n"
                for k, v in value.items():
                    body += f"  {k}: {v}\n"
            else:
                body += f"{key}: {value}\n"
        body += "```\n"

    return frontmatter + body


def extract_tool_defs_from_skills(skills) -> list[dict]:
    """从 Skill 模型列表中提取所有 tool 定义。

    批量调用 to_tool_def，用于 session 执行时一次性获取所有可用工具。
    """
    all_defs: list[dict] = []
    for skill in skills:
        manifest = getattr(skill, "manifest", {}) or {}
        defs = to_tool_def(manifest)
        if defs:
            logger.info("Extracted %d tool def(s) from skill '%s'", len(defs), skill.name)
            all_defs.extend(defs)
    return all_defs
