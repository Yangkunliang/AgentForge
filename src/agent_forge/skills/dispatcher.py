"""SkillDispatcher — 路由 LLM tool_call 到对应执行函数

职责：
  - 根据 tool function name 从 SkillRegistry 取执行函数
  - asyncio.wait_for 超时保护（默认 30s）
  - 把结果序列化为 JSON string（LLM tool role message 要求）
  - 通过 on_event 回调推送 SSE skill_called / skill_result 事件
  - 动态注入 user_id / on_event 到接受这些参数的 Skill 执行函数
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

logger = logging.getLogger(__name__)

SKILL_TIMEOUT_SECONDS = 30


class SkillDispatcher:
    """将 LLM 的 tool_call 分派到对应 Skill 执行函数"""

    def __init__(self) -> None:
        self._registry = get_skill_registry()

    async def invoke(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: dict[str, Any],
        on_event: Callable[[str, dict], Awaitable[None]] | None = None,
        user_id: str | None = None,
    ) -> str:
        """
        执行一次 tool_call，返回结果的 JSON 字符串。

        动态注入规则（检查 Skill 函数签名）：
          - 签名含 user_id  → 注入当前用户 ID
          - 签名含 on_event → 注入 SSE 事件回调，供 Skill 内部发射细粒度事件

        Args:
            tool_name:    LLM 指定调用的 function name，如 "code_executor"
            tool_call_id: LLM 返回的 tool_call id
            arguments:    LLM 传入的参数 dict
            on_event:     SSE 事件回调 async (event_type, data)
            user_id:      当前用户 ID

        Returns:
            JSON string，作为 tool role message 的 content 回传给 LLM
        """
        executor = self._registry.get_executor(tool_name)
        if executor is None:
            error_msg = f"未找到工具 '{tool_name}' 的执行函数，请检查 Skill 是否已注册。"
            logger.warning("SkillDispatcher: executor not found for '%s'", tool_name)
            return json.dumps({"error": error_msg}, ensure_ascii=False)

        # SSE: skill_called（内部事件，前端静默忽略）
        if on_event:
            await on_event("skill_called", {
                "tool": tool_name,
                "args": arguments,
                "tool_call_id": tool_call_id,
            })

        start_ms = int(time.monotonic() * 1000)
        try:
            # ── 动态参数注入 ─────────────────────────────────────────
            call_args = dict(arguments)
            sig = inspect.signature(executor)

            # 注入 user_id（仅函数签名声明时注入）
            if user_id is not None and "user_id" in sig.parameters:
                call_args["user_id"] = user_id

            # 注入 on_event（仅函数签名声明时注入）
            # 供 code_executor 等 Skill 内部发射 sandbox_executing 等细粒度事件
            if on_event is not None and "on_event" in sig.parameters:
                call_args["on_event"] = on_event

            result: Any = await asyncio.wait_for(
                executor(**call_args),
                timeout=SKILL_TIMEOUT_SECONDS,
            )
            elapsed_ms = int(time.monotonic() * 1000) - start_ms

            # 序列化结果
            if isinstance(result, str):
                result_str = result
            else:
                result_str = json.dumps(result, ensure_ascii=False, default=str)

            logger.info(
                "SkillDispatcher: '%s' completed in %dms, result_len=%d",
                tool_name, elapsed_ms, len(result_str),
            )

            # SSE: skill_result（内部事件，前端静默忽略）
            if on_event:
                await on_event("skill_result", {
                    "tool": tool_name,
                    "result": result_str[:500],
                    "elapsed_ms": elapsed_ms,
                    "tool_call_id": tool_call_id,
                })

            return result_str

        except asyncio.TimeoutError:
            elapsed_ms = int(time.monotonic() * 1000) - start_ms
            error_msg = f"工具 '{tool_name}' 执行超时（{SKILL_TIMEOUT_SECONDS}s），请稍后重试。"
            logger.error("SkillDispatcher: '%s' timed out after %dms", tool_name, elapsed_ms)
            if on_event:
                await on_event("skill_result", {
                    "tool": tool_name,
                    "error": "timeout",
                    "elapsed_ms": elapsed_ms,
                    "tool_call_id": tool_call_id,
                })
            return json.dumps({"error": error_msg}, ensure_ascii=False)

        except Exception as e:
            elapsed_ms = int(time.monotonic() * 1000) - start_ms
            error_msg = f"工具 '{tool_name}' 执行失败：{e}"
            logger.exception("SkillDispatcher: '%s' raised exception: %s", tool_name, e)
            if on_event:
                await on_event("skill_result", {
                    "tool": tool_name,
                    "error": str(e),
                    "elapsed_ms": elapsed_ms,
                    "tool_call_id": tool_call_id,
                })
            return json.dumps({"error": error_msg}, ensure_ascii=False)
