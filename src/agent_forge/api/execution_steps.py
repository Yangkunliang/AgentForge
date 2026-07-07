"""Collect SSE events into persisted chat execution steps."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CODE_EXECUTOR_TOOL = "code_executor"
TIMEOUT_MESSAGE = "执行超时(超过 30 秒), 请简化代码或检查死循环。"


class ExecutionStepCollector:
    """Build the message.extra_data execution step list from SSE events."""

    def __init__(self) -> None:
        self.steps: list[dict[str, Any]] = []
        self._pending_code_arguments: dict[str, Any] = {}

    def collect(self, event_type: str, data: Mapping[str, Any] | None = None) -> None:
        event_data = data or {}

        if event_type == "thinking_start":
            self.steps.append({"type": "thinking", "content": "", "streaming": True})
        elif event_type == "thinking_delta":
            self._append_thinking_delta(str(event_data.get("delta", "")))
        elif event_type == "thinking_end":
            self._end_thinking(event_data)
        elif event_type == "tool_call_start":
            self._start_tool_call(event_data)
        elif event_type == "tool_call_end":
            self._end_tool_call(event_data)
        elif event_type == "sandbox_executing":
            self._start_code_execution(str(event_data.get("code", "")))
        elif event_type == "sandbox_completed":
            self._complete_code_execution(event_data)
        elif event_type == "sandbox_timeout":
            self._timeout_code_execution()

    def _append_thinking_delta(self, delta: str) -> None:
        step = self._latest_thinking(streaming=True)
        if step is None:
            self.steps.append({"type": "thinking", "content": delta, "streaming": True})
            return
        step["content"] += delta

    def _end_thinking(self, data: Mapping[str, Any]) -> None:
        step = self._latest_thinking(streaming=True)
        if step is None:
            return
        step["streaming"] = False
        step["duration_ms"] = data.get("duration_ms", 0)

    def _start_tool_call(self, data: Mapping[str, Any]) -> None:
        tool_name = str(data.get("tool_name", ""))
        arguments = self._as_dict(data.get("arguments"))

        if tool_name == CODE_EXECUTOR_TOOL:
            self._pending_code_arguments = arguments
            return

        self.steps.append({
            "type": "tool_call",
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "running",
        })

    def _end_tool_call(self, data: Mapping[str, Any]) -> None:
        tool_name = str(data.get("tool_name", ""))
        result = self._as_dict(data.get("result"))

        if tool_name == CODE_EXECUTOR_TOOL:
            self._finish_code_executor(data, result)
            return

        step = self._latest_tool_call(tool_name)
        if step is None:
            return

        step["status"] = "failed" if self._is_error_result(result) else "completed"
        step["result"] = result
        if "duration_ms" in data:
            step["duration_ms"] = data.get("duration_ms")

    def _start_code_execution(self, code: str) -> None:
        self.steps.append({
            "type": "code_execution",
            "code": code,
            "status": "running",
            "stdout": "",
            "stderr": "",
        })

    def _complete_code_execution(self, data: Mapping[str, Any]) -> None:
        step = self._latest_code_execution(include_finished=False)
        if step is None:
            return

        step["status"] = "completed"
        step["exit_code"] = data.get("exit_code", 0)
        step["duration_ms"] = data.get("duration_ms", 0)

    def _timeout_code_execution(self) -> None:
        step = self._latest_code_execution(include_finished=False)
        if step is None:
            return

        step["status"] = "timeout"
        step["stderr"] = TIMEOUT_MESSAGE

    def _finish_code_executor(self, data: Mapping[str, Any], result: dict[str, Any]) -> None:
        step = self._latest_code_execution(include_finished=True)
        if step is None:
            arguments = self._as_dict(data.get("arguments")) or self._pending_code_arguments
            self._start_code_execution(str(arguments.get("code", "")))
            step = self._latest_code_execution(include_finished=True)
            if step is None:
                return

        status = "failed" if self._is_error_result(result) else "completed"
        if step.get("status") == "timeout":
            status = "timeout"

        step["status"] = status
        step["stdout"] = str(result.get("stdout", step.get("stdout", "")))
        step["stderr"] = str(result.get("stderr", step.get("stderr", "")))
        step["exit_code"] = result.get("exit_code", step.get("exit_code", 0))
        step["duration_ms"] = result.get("duration_ms", data.get("duration_ms", step.get("duration_ms", 0)))

    def _latest_thinking(self, streaming: bool) -> dict[str, Any] | None:
        for step in reversed(self.steps):
            if step.get("type") == "thinking" and step.get("streaming") is streaming:
                return step
        return None

    def _latest_tool_call(self, tool_name: str) -> dict[str, Any] | None:
        for step in reversed(self.steps):
            if (
                step.get("type") == "tool_call"
                and step.get("tool_name") == tool_name
                and step.get("status") == "running"
            ):
                return step
        return None

    def _latest_code_execution(self, *, include_finished: bool) -> dict[str, Any] | None:
        for step in reversed(self.steps):
            if step.get("type") != "code_execution":
                continue
            if include_finished or step.get("status") == "running":
                return step
        return None

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _is_error_result(result: Mapping[str, Any]) -> bool:
        return bool(result.get("error")) or result.get("success") is False
