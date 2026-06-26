"""
agent_forge.agents.coder
=========================
Coder Agent：代码生成 + 沙箱执行 + 自动修复 Agent。

工作流
------
1. LLM 根据需求描述生成 Python 代码
2. 通过 SandboxManager 在隔离沙箱中执行
3. 如果执行失败（stderr 非空 / exit_code != 0），将错误信息反馈给 LLM 自动修复
4. 最多重试 MAX_FIX_ROUNDS 次，仍失败则返回最终错误

用法示例
--------
    from agent_forge.agents.coder import CoderAgent, CoderConfig

    agent = CoderAgent(config=CoderConfig(), llm_provider=provider)
    result = await agent.run(
        task_id="task-123",
        description="实现一个计算斐波那契数列的函数并打印前 10 项",
    )
    # result = {
    #     "success": True,
    #     "code": "...",
    #     "stdout": "...",
    #     "stderr": "",
    #     "exit_code": 0,
    #     "rounds": 1,
    # }
"""

from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass, field
from typing import Any

from agent_forge.config import sandbox_settings
from agent_forge.sandbox.base import ExecResult, SandboxDestroyedError, SandboxTimeoutError
from agent_forge.sandbox.factory import SandboxProviderFactory
from agent_forge.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

# 每次任务最多尝试修复的轮数
MAX_FIX_ROUNDS = 3


@dataclass
class CoderConfig:
    """Coder Agent 配置。

    Attributes:
        model:         生成代码使用的模型（通过 LLMProvider 传入，此处仅作说明）
        temperature:   LLM 采样温度
        max_fix_rounds: 最大自动修复轮数
        sandbox_timeout: 每次代码执行的超时秒数
    """
    model: str = ""
    temperature: float = 0.2      # 代码生成用较低温度
    max_fix_rounds: int = MAX_FIX_ROUNDS
    sandbox_timeout: int = 30


class CoderAgent:
    """代码生成 + 沙箱执行 + 自动修复 Agent。

    不依赖 BaseAgent 继承，直接接受 llm_provider 调用接口，
    以便在不同 Harness 接入点复用。

    Args:
        config:         CoderConfig 实例
        llm_provider:   实现 `.complete(prompt, config) -> LLMResponse` 的提供者
    """

    def __init__(self, config: CoderConfig | None = None, llm_provider: Any = None) -> None:
        self._config = config or CoderConfig()
        self._llm = llm_provider
        self._executor = SandboxProviderFactory.create(
            provider=sandbox_settings.cube_sandbox_default_provider,
            url=sandbox_settings.cube_sandbox_url,
            api_key=sandbox_settings.cube_sandbox_api_key,
            template_id=sandbox_settings.cube_template_id,
        )

    async def run(
        self,
        description: str,
        *,
        task_id: str = "",
        extra_context: str = "",
    ) -> dict[str, Any]:
        """执行代码任务的完整工作流。

        Args:
            description:    自然语言描述的编程需求
            task_id:        所属任务 ID（用于 SSE 事件推送）
            extra_context:  附加上下文（如已有代码片段、依赖说明等）

        Returns:
            dict，包含 success / code / stdout / stderr / exit_code / rounds / error
        """
        manager = SandboxManager(
            executor=self._executor,
            ttl_seconds=sandbox_settings.cube_sandbox_timeout,
        )

        code = ""
        last_result: ExecResult | None = None
        error_msg = ""

        try:
            for round_num in range(1, self._config.max_fix_rounds + 1):
                logger.info(
                    "CoderAgent: round=%d task_id=%s", round_num, task_id
                )

                # ── 1. 推送 SSE 代码执行事件 ─────────────────────────────
                if task_id:
                    await self._emit_executing(task_id, manager, code)

                # ── 2. 生成代码 ───────────────────────────────────────────
                if round_num == 1:
                    code = await self._generate_code(description, extra_context)
                else:
                    # 修复轮：将 stderr 反馈给 LLM
                    code = await self._fix_code(
                        description=description,
                        previous_code=code,
                        stderr=last_result.stderr if last_result else error_msg,
                        stdout=last_result.stdout if last_result else "",
                    )

                if not code.strip():
                    logger.warning("CoderAgent: LLM returned empty code, aborting")
                    break

                # ── 3. 沙箱执行 ───────────────────────────────────────────
                try:
                    last_result = await manager.execute(
                        code, timeout=self._config.sandbox_timeout
                    )
                except SandboxTimeoutError as e:
                    error_msg = str(e)
                    logger.warning("CoderAgent: execution timeout in round %d", round_num)
                    if task_id:
                        await self._emit_completed(task_id, manager, -1, 0)
                    # 超时不再重试（无意义）
                    return {
                        "success": False,
                        "code": code,
                        "stdout": "",
                        "stderr": error_msg,
                        "exit_code": -1,
                        "rounds": round_num,
                        "error": "timeout",
                    }

                # ── 4. 推送执行结果 SSE ───────────────────────────────────
                if task_id:
                    await self._emit_completed(
                        task_id, manager,
                        last_result.exit_code,
                        last_result.duration_ms,
                    )

                # ── 5. 判断是否成功 ───────────────────────────────────────
                if last_result.exit_code == 0 and not last_result.stderr:
                    logger.info(
                        "CoderAgent: success in round=%d, duration=%dms",
                        round_num, last_result.duration_ms,
                    )
                    return {
                        "success": True,
                        "code": code,
                        "stdout": last_result.stdout,
                        "stderr": last_result.stderr,
                        "exit_code": last_result.exit_code,
                        "duration_ms": last_result.duration_ms,
                        "rounds": round_num,
                    }

                logger.info(
                    "CoderAgent: round=%d failed (exit_code=%d), will retry",
                    round_num, last_result.exit_code,
                )

            # 超过最大修复轮数仍失败
            return {
                "success": False,
                "code": code,
                "stdout": last_result.stdout if last_result else "",
                "stderr": last_result.stderr if last_result else error_msg,
                "exit_code": last_result.exit_code if last_result else -1,
                "rounds": self._config.max_fix_rounds,
                "error": "max_fix_rounds_exceeded",
            }

        except SandboxDestroyedError as e:
            return {
                "success": False,
                "code": code,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "rounds": 0,
                "error": "sandbox_destroyed",
            }

        finally:
            await manager.destroy()

    # ── LLM 调用 ─────────────────────────────────────────────────────

    async def _generate_code(self, description: str, extra_context: str = "") -> str:
        """调用 LLM 生成 Python 代码。"""
        context_block = (
            f"\n\n参考上下文：\n{extra_context}" if extra_context else ""
        )
        prompt = textwrap.dedent(f"""
            你是一位专业的 Python 工程师。请根据以下需求编写可直接运行的 Python 代码。

            需求描述：
            {description}{context_block}

            要求：
            - 只输出可运行的 Python 代码，不包含任何说明文字
            - 不要使用 Markdown 代码块（不要包含 ```python）
            - 代码必须能在标准 Python 3.9+ 环境中直接运行
            - 如果需要打印结果，使用 print()
        """).strip()

        if self._llm is None:
            logger.warning("CoderAgent: no LLM provider, returning placeholder code")
            return f"# 需求：{description}\nprint('no LLM provider')"

        try:
            from agent_forge.llm import LLMConfig
            response = await self._llm.complete(
                prompt,
                LLMConfig(model=self._config.model, temperature=self._config.temperature),
            )
            return self._strip_code_fence(response.content)
        except Exception as e:
            logger.error("CoderAgent: LLM code generation failed: %s", e)
            return ""

    async def _fix_code(
        self,
        description: str,
        previous_code: str,
        stderr: str,
        stdout: str,
    ) -> str:
        """根据执行错误让 LLM 修复代码。"""
        prompt = textwrap.dedent(f"""
            你是一位专业的 Python 工程师。你之前生成的代码在执行时出现了错误，
            请根据错误信息修复代码。

            原始需求：{description}

            之前的代码：
            {previous_code}

            执行错误（stderr）：
            {stderr}

            标准输出（stdout）：
            {stdout}

            请输出修复后的完整 Python 代码：
            - 只输出代码，不包含任何说明文字
            - 不要使用 Markdown 代码块
        """).strip()

        if self._llm is None:
            return previous_code

        try:
            from agent_forge.llm import LLMConfig
            response = await self._llm.complete(
                prompt,
                LLMConfig(model=self._config.model, temperature=self._config.temperature),
            )
            return self._strip_code_fence(response.content)
        except Exception as e:
            logger.error("CoderAgent: LLM fix failed: %s", e)
            return previous_code

    # ── SSE 事件 ──────────────────────────────────────────────────────

    @staticmethod
    async def _emit_executing(
        task_id: str, manager: SandboxManager, code: str
    ) -> None:
        """推送沙箱代码执行开始 SSE 事件。"""
        try:
            from agent_forge.api.sse import emit_sandbox_code_executing
            sid = manager.sandbox_id or "pending"
            await emit_sandbox_code_executing(task_id, sid, code[:200])
        except Exception:
            pass  # SSE 推送失败不影响执行

    @staticmethod
    async def _emit_completed(
        task_id: str, manager: SandboxManager, exit_code: int, duration_ms: int
    ) -> None:
        """推送沙箱代码执行完成 SSE 事件。"""
        try:
            from agent_forge.api.sse import emit_sandbox_code_completed
            sid = manager.sandbox_id or "unknown"
            await emit_sandbox_code_completed(task_id, sid, exit_code, duration_ms)
        except Exception:
            pass

    # ── 工具方法 ──────────────────────────────────────────────────────

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """去除 LLM 返回的 Markdown 代码块围栏。"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # 去除第一行（```python 或 ```）
            lines = lines[1:]
            # 去除最后一行（```）
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text
