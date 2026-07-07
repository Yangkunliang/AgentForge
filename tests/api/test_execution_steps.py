from __future__ import annotations

from agent_forge.api.execution_steps import ExecutionStepCollector


def test_collects_thinking_stream_lifecycle() -> None:
    collector = ExecutionStepCollector()

    collector.collect("thinking_start", {})
    collector.collect("thinking_delta", {"delta": "分析"})
    collector.collect("thinking_delta", {"delta": "需求"})
    collector.collect("thinking_end", {"duration_ms": 123})

    assert collector.steps == [
        {
            "type": "thinking",
            "content": "分析需求",
            "streaming": False,
            "duration_ms": 123,
        }
    ]


def test_code_executor_uses_single_code_execution_step() -> None:
    collector = ExecutionStepCollector()

    collector.collect(
        "tool_call_start",
        {"tool_name": "code_executor", "arguments": {"code": "print('hi')"}},
    )
    collector.collect("sandbox_executing", {"code": "print('hi')"})
    collector.collect("sandbox_completed", {"exit_code": 0, "duration_ms": 42})
    collector.collect(
        "tool_call_end",
        {
            "tool_name": "code_executor",
            "result": {
                "success": True,
                "stdout": "hi\n",
                "stderr": "",
                "exit_code": 0,
                "duration_ms": 42,
            },
        },
    )

    assert collector.steps == [
        {
            "type": "code_execution",
            "code": "print('hi')",
            "status": "completed",
            "stdout": "hi\n",
            "stderr": "",
            "exit_code": 0,
            "duration_ms": 42,
        }
    ]


def test_code_executor_error_without_sandbox_event_creates_failed_code_step() -> None:
    collector = ExecutionStepCollector()

    collector.collect(
        "tool_call_start",
        {"tool_name": "code_executor", "arguments": {"code": "import os"}},
    )
    collector.collect(
        "tool_call_end",
        {
            "tool_name": "code_executor",
            "arguments": {"code": "import os"},
            "result": {
                "success": False,
                "stdout": "",
                "stderr": "[安全拦截] 禁止导入 os。",
                "exit_code": -1,
                "duration_ms": 0,
                "error": "blocked_unsafe_code",
            },
        },
    )

    assert collector.steps == [
        {
            "type": "code_execution",
            "code": "import os",
            "status": "failed",
            "stdout": "",
            "stderr": "[安全拦截] 禁止导入 os。",
            "exit_code": -1,
            "duration_ms": 0,
        }
    ]


def test_generic_tool_error_result_marks_step_failed() -> None:
    collector = ExecutionStepCollector()

    collector.collect("tool_call_start", {"tool_name": "get_weather", "arguments": {"city": "厦门"}})
    collector.collect(
        "tool_call_end",
        {
            "tool_name": "get_weather",
            "result": {"error": "天气服务不可用"},
        },
    )

    assert collector.steps == [
        {
            "type": "tool_call",
            "tool_name": "get_weather",
            "arguments": {"city": "厦门"},
            "status": "failed",
            "result": {"error": "天气服务不可用"},
        }
    ]


def test_keeps_multi_step_order_by_event_arrival() -> None:
    collector = ExecutionStepCollector()

    collector.collect("thinking_start", {})
    collector.collect("thinking_delta", {"delta": "先查天气"})
    collector.collect("thinking_end", {"duration_ms": 10})
    collector.collect("tool_call_start", {"tool_name": "get_weather", "arguments": {"city": "厦门"}})
    collector.collect("tool_call_end", {"tool_name": "get_weather", "result": {"temperature": "27C"}})
    collector.collect("thinking_start", {})
    collector.collect("thinking_delta", {"delta": "再汇总"})
    collector.collect("thinking_end", {"duration_ms": 20})

    assert [step["type"] for step in collector.steps] == ["thinking", "tool_call", "thinking"]
    assert collector.steps[1]["tool_name"] == "get_weather"
    assert collector.steps[2]["content"] == "再汇总"


def test_sandbox_timeout_marks_latest_code_execution_step() -> None:
    collector = ExecutionStepCollector()

    collector.collect("sandbox_executing", {"code": "while True: pass"})
    collector.collect("sandbox_timeout", {"timeout_seconds": 30})

    assert collector.steps == [
        {
            "type": "code_execution",
            "code": "while True: pass",
            "status": "timeout",
            "stdout": "",
            "stderr": "执行超时(超过 30 秒), 请简化代码或检查死循环。",
        }
    ]
