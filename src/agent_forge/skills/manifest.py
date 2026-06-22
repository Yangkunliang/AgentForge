"""Skill Manifest 解析器

解析 skill.md 文件，提取 frontmatter 元数据和工具定义，
并将 manifest 转换为 OpenAI tools format 供 LLM tool_use 使用。
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


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
