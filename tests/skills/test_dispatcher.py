"""SkillDispatcher 单元测试"""

from __future__ import annotations

import json
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from agent_forge.skills.dispatcher import SkillDispatcher, SKILL_TIMEOUT_SECONDS
from agent_forge.skills.registry import get_skill_registry


@pytest.mark.asyncio
class TestSkillDispatcher:
    """SkillDispatcher 测试"""

    async def test_invoke_tool_not_found(self):
        dispatcher = SkillDispatcher()
        result = await dispatcher.invoke(
            tool_name="nonexistent_tool",
            tool_call_id="test-id",
            arguments={},
        )
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_invoke_tool_success(self):
        registry = get_skill_registry()

        async def mock_executor(**kwargs):
            return {"result": "success", "args": kwargs}

        tool_def = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "Test tool",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        }
        registry.register(
            skill_name="test-skill",
            tool_defs=[tool_def],
            executors={"test_tool": mock_executor},
        )

        dispatcher = SkillDispatcher()
        result = await dispatcher.invoke(
            tool_name="test_tool",
            tool_call_id="test-id",
            arguments={"name": "test"},
        )
        parsed = json.loads(result)
        assert parsed["result"] == "success"

        registry.unregister("test-skill")

    async def test_invoke_tool_timeout(self):
        registry = get_skill_registry()

        async def slow_executor(**kwargs):
            await asyncio.sleep(SKILL_TIMEOUT_SECONDS + 1)
            return {"result": "delayed"}

        tool_def = {
            "type": "function",
            "function": {
                "name": "slow_tool",
                "description": "Slow tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        registry.register(
            skill_name="test-skill",
            tool_defs=[tool_def],
            executors={"slow_tool": slow_executor},
        )

        dispatcher = SkillDispatcher()
        result = await dispatcher.invoke(
            tool_name="slow_tool",
            tool_call_id="test-id",
            arguments={},
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "超时" in parsed["error"]

        registry.unregister("test-skill")

    async def test_invoke_tool_exception(self):
        registry = get_skill_registry()

        async def error_executor(**kwargs):
            raise ValueError("Test error")

        tool_def = {
            "type": "function",
            "function": {
                "name": "error_tool",
                "description": "Error tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        registry.register(
            skill_name="test-skill",
            tool_defs=[tool_def],
            executors={"error_tool": error_executor},
        )

        dispatcher = SkillDispatcher()
        result = await dispatcher.invoke(
            tool_name="error_tool",
            tool_call_id="test-id",
            arguments={},
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Test error" in parsed["error"]

        registry.unregister("test-skill")

    async def test_invoke_with_event_callback(self):
        events = []

        async def on_event(event_type, data):
            events.append((event_type, data))

        registry = get_skill_registry()

        async def mock_executor(**kwargs):
            return {"result": "success"}

        tool_def = {
            "type": "function",
            "function": {
                "name": "event_tool",
                "description": "Event tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        registry.register(
            skill_name="test-skill",
            tool_defs=[tool_def],
            executors={"event_tool": mock_executor},
        )

        dispatcher = SkillDispatcher()
        await dispatcher.invoke(
            tool_name="event_tool",
            tool_call_id="test-id",
            arguments={"key": "value"},
            on_event=on_event,
        )

        assert len(events) >= 2
        event_types = [e[0] for e in events]
        assert "skill_called" in event_types
        assert "skill_result" in event_types

        skill_called_data = next(e[1] for e in events if e[0] == "skill_called")
        assert skill_called_data["tool"] == "event_tool"
        assert skill_called_data["args"] == {"key": "value"}

        registry.unregister("test-skill")