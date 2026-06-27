"""SkillDispatcher — 路由 LLM tool_call 到对应执行函数

职责：
  - 根据 tool function name 从 SkillRegistry 取执行函数
  - asyncio.wait_for 超时保护（默认 30s）
  - 结果序列化为 JSON string
  - 通过 on_event 回调推送 SSE skill_called / skill_result 事件
  - 动态注入 user_id / on_event 到接受这些参数的 Skill 执行函数

Tracing（TASK-010）
--------------------
invoke() 用 @span 自动采集每次工具调用耗时，
span tags 包含 tool_name / elapsed_ms / error，
无需在业务层手动打日志。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from agent_forge.skills.registry import get_skill_registry
from agent_forge.tracing import get_current_span, span

logger = logging.getLogger(__name__)

SKILL_TIMEOUT_SECONDS = 30


class SkillDispatcher:

    def __init__(self) -> None:
        self._registry = get_skill_registry()

    @span("skill.invoke")
    async def invoke(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: dict[str, Any],
        on_event: Callable[[str, dict], Awaitable[None]] | None = None,
        user_id: str | None = None,
    ) -> str:
        """执行一次 tool_call，返回结果 JSON 字符串。

        span tags 自动写入：tool_name / success / elapsed_ms
        """
        # 把 tool_name 写入当前 span，让 trace 日志能直接看出调用了哪个工具
        sp = get_current_span()
        if sp:
            sp.tags["tool"] = tool_name
            sp.tags["tool_call_id"] = tool_call_id[:8]

        executor = self._registry.get_executor(tool_name)
        if executor is None:
            err = f"未找到工具 '{tool_name}' 的执行函数，请检查 Skill 是否已注册。"
            logger.warning("SkillDispatcher: executor not found for '%s'", tool_name)
            if sp:
                sp.tags["error"] = "not_found"
            return json.dumps({"error": err}, ensure_ascii=False)

        if on_event:
            await on_event("skill_called", {
                "tool": tool_name,
                "args": arguments,
                "tool_call_id": tool_call_id,
            })

        t0 = time.monotonic()
        try:
            call_args = dict(arguments)
            sig = inspect.signature(executor)

            if user_id is not None and "user_id" in sig.parameters:
                call_args["user_id"] = user_id
            if on_event is not None and "on_event" in sig.parameters:
                call_args["on_event"] = on_event

            result: Any = await asyncio.wait_for(
                executor(**call_args),
                timeout=SKILL_TIMEOUT_SECONDS,
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            result_str = result if isinstance(result, str) else json.dumps(
                result, ensure_ascii=False, default=str)

            if sp:
                sp.tags.update({"elapsed_ms": elapsed_ms, "success": True,
                                 "result_len": len(result_str)})

            logger.info("SkillDispatcher: '%s' ok in %dms", tool_name, elapsed_ms)

            if on_event:
                await on_event("skill_result", {
                    "tool": tool_name,
                    "result": result_str[:500],
                    "elapsed_ms": elapsed_ms,
                    "tool_call_id": tool_call_id,
                })

            return result_str

        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            err = f"工具 '{tool_name}' 执行超时（{SKILL_TIMEOUT_SECONDS}s）。"
            logger.error("SkillDispatcher: '%s' timeout after %dms", tool_name, elapsed_ms)
            if sp:
                sp.tags.update({"elapsed_ms": elapsed_ms, "error": "timeout"})
            if on_event:
                await on_event("skill_result", {
                    "tool": tool_name, "error": "timeout",
                    "elapsed_ms": elapsed_ms, "tool_call_id": tool_call_id,
                })
            return json.dumps({"error": err}, ensure_ascii=False)

        except Exception as e:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            err = f"工具 '{tool_name}' 执行失败：{e}"
            logger.exception("SkillDispatcher: '%s' error: %s", tool_name, e)
            if sp:
                sp.tags.update({"elapsed_ms": elapsed_ms, "error": str(e)[:100]})
            if on_event:
                await on_event("skill_result", {
                    "tool": tool_name, "error": str(e),
                    "elapsed_ms": elapsed_ms, "tool_call_id": tool_call_id,
                })
            return json.dumps({"error": err}, ensure_ascii=False)
