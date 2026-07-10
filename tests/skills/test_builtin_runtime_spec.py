"""Built-in Skill runtime spec tests."""

from __future__ import annotations

import pytest

from agent_forge.skills.builtin import register_builtin_skills
from agent_forge.skills.policy import filter_tool_defs_for_runtime
from agent_forge.skills.registry import get_skill_registry
from agent_forge.skills.runtime_spec import classify_permission_risk, normalize_permissions


BUILTIN_SKILLS = [
    "web-search",
    "weather",
    "http-request",
    "update-profile",
    "code-executor",
]


@pytest.mark.asyncio
async def test_register_builtin_skills_adds_runtime_specs_and_filters_high_risk_tools(db_session):
    registry = get_skill_registry()
    for skill_name in BUILTIN_SKILLS:
        registry.unregister(skill_name)

    assert normalize_permissions(["external_side_effect"]) == ["external_side_effect"]
    assert classify_permission_risk(["external_side_effect"]) == "high"

    await register_builtin_skills(db_session)

    try:
        specs = {name: registry.get_runtime_spec(name) for name in BUILTIN_SKILLS}

        assert specs["web-search"]["source_type"] == "builtin"
        assert specs["web-search"]["permissions"] == ["network"]
        assert specs["weather"]["permissions"] == ["network"]
        assert specs["http-request"]["permissions"] == ["network", "external_side_effect"]
        assert specs["update-profile"]["permissions"] == ["external_side_effect"]
        assert specs["code-executor"]["permissions"] == ["shell"]
        assert specs["code-executor"]["requires_confirmation"] is True

        builtin_tools = [
            tool
            for tool in registry.get_all_tool_defs()
            if registry.get_skill_name_for_tool(tool["function"]["name"]) in BUILTIN_SKILLS
        ]
        filtered, report = filter_tool_defs_for_runtime(
            builtin_tools,
            registry=registry,
            skill_policy_key="default",
        )

        assert [tool["function"]["name"] for tool in filtered] == ["web_search", "get_weather"]
        assert {
            (item["tool_name"], item["skill_name"], item["reason"], tuple(item["permissions"]))
            for item in report.excluded_tools
        } == {
            ("http_request", "http-request", "permission_denied", ("network", "external_side_effect")),
            ("update_profile", "update-profile", "permission_denied", ("external_side_effect",)),
            ("code_executor", "code-executor", "permission_denied", ("shell",)),
        }
    finally:
        for skill_name in BUILTIN_SKILLS:
            registry.unregister(skill_name)
