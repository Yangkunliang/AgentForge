"""Distill a developer's expertise from free-form text via LLM.

This is the literal "capability distillation" entry point: a user pastes real
work artifacts (PR reviews, commit messages, design notes) and we ask the LLM
to extract them into a structured :class:`AgentExpertise` that the runtime can
later inject into the system-prompt trusted region.
"""

from __future__ import annotations

import json
import re
from typing import Any

from agent_forge.agents.expertise import AgentExpertise
from agent_forge.config import settings
from agent_forge.llm.provider import LLMConfig, get_llm_provider

_EXTRACT_SYSTEM_PROMPT = """你是一个资深的工程能力蒸馏专家。用户会提供一位开发者的真实工作素材，例如：代码评审意见（PR review）、提交记录（commit messages）、技术讨论、编码规范文档等。你的任务是把其中体现的个人工程能力，抽取成结构化的「专家模型」，供 AI Agent 在运行时遵循。

请严格只输出一个 JSON 对象，字段如下（不存在的信号就留空字符串 / 空数组 / 空对象，不要编造）：

{
  "role_title": "用一句话概括这位开发者的角色（如：资深全栈工程师）",
  "summary": "用 1-3 句话概括其工程风格与强项",
  "conventions": {
    "naming": ["命名规范类条目"],
    "formatting": ["格式/缩进类条目"],
    "architecture": ["架构/分层类条目"],
    "testing": ["测试相关条目"]
  },
  "review_checklist": ["代码审查时必查的事项，逐条"],
  "tech_preferences": {
    "frontend": ["前端技术偏好"],
    "backend": ["后端技术偏好"],
    "database": ["数据库偏好"],
    "devops": ["运维/部署偏好"],
    "avoid": ["明确不喜欢的技術或做法"]
  },
  "anti_patterns": ["这位开发者反复强调要避免的反模式 / 雷区，逐条"],
  "debugging_heuristics": ["其调试套路 / 排障思路，逐条"],
  "communication_style": "其输出 / 沟通风格（如：结论先行、给可复制命令、用示例说话）"
}

要求：
1. 只从素材中提炼真实存在的信号，宁缺毋滥，不要无中生有。
2. 条目要具体、可执行，避免空话（如「写高质量代码」这种无效）。
3. 只输出 JSON，不要任何解释，不要 markdown 代码块围栏。
"""


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort parse of a JSON object out of an LLM response."""
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


async def extract_expertise(
    source_text: str,
    role_hint: str | None = None,
) -> AgentExpertise:
    """Extract a structured :class:`AgentExpertise` from free-form text.

    Uses the project's configured default LLM with a low temperature for
    deterministic, signal-only extraction.
    """
    provider = get_llm_provider()
    body = source_text.strip()
    if not body:
        return AgentExpertise()

    if role_hint:
        user_msg = f"【角色提示】{role_hint}\n\n素材如下：\n{body}"
    else:
        user_msg = f"素材如下：\n{body}"

    config = LLMConfig(
        model=settings.default_model,
        temperature=0.2,
        max_tokens=2048,
    )
    resp = await provider.chat_complete(
        messages=[
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        config=config,
    )
    data = _extract_json(resp.content)
    if not isinstance(data, dict):
        raise ValueError("LLM 未返回有效的 expertise JSON")
    return AgentExpertise.from_dict(data)
