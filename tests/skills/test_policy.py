"""Skill runtime filtering policy tests."""

from __future__ import annotations

from agent_forge.skills.policy import filter_tool_defs_for_runtime
from agent_forge.skills.registry import get_skill_registry


def _tool_def(name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"{name} test tool",
            "parameters": {"type": "object", "properties": {}},
        },
    }


async def _executor(**_kwargs):
    return {"ok": True}


def test_filter_tool_defs_applies_stage_permissions_and_agent_allowlist():
    registry = get_skill_registry()
    safe_tool = _tool_def("policy_safe_tool")
    shell_tool = _tool_def("policy_shell_tool")
    research_tool = _tool_def("policy_research_tool")

    registry.register(
        skill_name="safe-skill",
        tool_defs=[safe_tool],
        executors={"policy_safe_tool": _executor},
        runtime_spec={
            "name": "safe-skill",
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "safe-hash",
            "permissions": ["network"],
            "executor_kind": "python",
        },
    )
    registry.register(
        skill_name="shell-skill",
        tool_defs=[shell_tool],
        executors={"policy_shell_tool": _executor},
        runtime_spec={
            "name": "shell-skill",
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "shell-hash",
            "permissions": ["shell"],
            "executor_kind": "python",
        },
    )
    registry.register(
        skill_name="research-skill",
        tool_defs=[research_tool],
        executors={"policy_research_tool": _executor},
        runtime_spec={
            "name": "research-skill",
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "research-hash",
            "permissions": ["project_context"],
            "executor_kind": "python",
        },
    )

    try:
        filtered, report = filter_tool_defs_for_runtime(
            [safe_tool, shell_tool, research_tool],
            registry=registry,
            skill_policy_key="default",
            agent_allowed_skill_names=["safe-skill", "shell-skill"],
        )
    finally:
        registry.unregister("safe-skill")
        registry.unregister("shell-skill")
        registry.unregister("research-skill")

    assert [tool["function"]["name"] for tool in filtered] == ["policy_safe_tool"]
    assert report.input_tool_count == 3
    assert report.allowed_tool_count == 1
    assert {
        (item["tool_name"], item["skill_name"], item["reason"])
        for item in report.excluded_tools
    } == {
        ("policy_shell_tool", "shell-skill", "permission_denied"),
        ("policy_research_tool", "research-skill", "agent_not_allowed"),
    }


def test_filter_tool_defs_accepts_temporary_high_risk_authorization():
    registry = get_skill_registry()
    shell_tool = _tool_def("policy_authorized_shell_tool")
    side_effect_tool = _tool_def("policy_side_effect_tool")

    registry.register(
        skill_name="authorized-shell-skill",
        tool_defs=[shell_tool],
        executors={"policy_authorized_shell_tool": _executor},
        runtime_spec={
            "name": "authorized-shell-skill",
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "authorized-shell-hash",
            "permissions": ["shell"],
            "executor_kind": "python",
        },
    )
    registry.register(
        skill_name="external-side-effect-skill",
        tool_defs=[side_effect_tool],
        executors={"policy_side_effect_tool": _executor},
        runtime_spec={
            "name": "external-side-effect-skill",
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "side-effect-hash",
            "permissions": ["external_side_effect"],
            "executor_kind": "python",
        },
    )

    try:
        filtered, report = filter_tool_defs_for_runtime(
            [shell_tool, side_effect_tool],
            registry=registry,
            skill_policy_key="default",
            agent_allowed_skill_names=[
                "authorized-shell-skill",
                "external-side-effect-skill",
            ],
            authorized_skill_names=["authorized-shell-skill"],
            authorized_permissions=["shell"],
        )
    finally:
        registry.unregister("authorized-shell-skill")
        registry.unregister("external-side-effect-skill")

    assert [tool["function"]["name"] for tool in filtered] == ["policy_authorized_shell_tool"]
    assert report.authorized_skill_names == ["authorized-shell-skill"]
    assert report.authorized_permissions == ["shell"]
    assert report.to_context()["authorized_skill_names"] == ["authorized-shell-skill"]
    assert report.excluded_tools == [
        {
            "tool_name": "policy_side_effect_tool",
            "skill_name": "external-side-effect-skill",
            "reason": "permission_denied",
            "permissions": ["external_side_effect"],
        }
    ]


def test_temporary_high_risk_authorization_does_not_override_agent_allowlist():
    registry = get_skill_registry()
    shell_tool = _tool_def("policy_unbound_shell_tool")

    registry.register(
        skill_name="unbound-shell-skill",
        tool_defs=[shell_tool],
        executors={"policy_unbound_shell_tool": _executor},
        runtime_spec={
            "name": "unbound-shell-skill",
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "unbound-shell-hash",
            "permissions": ["shell"],
            "executor_kind": "python",
        },
    )

    try:
        filtered, report = filter_tool_defs_for_runtime(
            [shell_tool],
            registry=registry,
            skill_policy_key="default",
            agent_allowed_skill_names=["safe-skill"],
            authorized_skill_names=["unbound-shell-skill"],
            authorized_permissions=["shell"],
        )
    finally:
        registry.unregister("unbound-shell-skill")

    assert filtered == []
    assert report.excluded_tools == [
        {
            "tool_name": "policy_unbound_shell_tool",
            "skill_name": "unbound-shell-skill",
            "reason": "agent_not_allowed",
            "permissions": ["shell"],
        }
    ]
