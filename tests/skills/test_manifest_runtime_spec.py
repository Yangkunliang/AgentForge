from __future__ import annotations

import textwrap

import pytest

from agent_forge.skills.manifest import SkillManifestError, load_skill_manifest


def test_load_agentforge_skill_manifest_builds_runtime_preview(tmp_path):
    skill_dir = tmp_path / "safe-echo"
    skill_dir.mkdir()
    manifest_path = skill_dir / "agentforge-skill.yaml"
    manifest_path.write_text(
        textwrap.dedent(
            """
            name: safe-echo
            version: 1.2.0
            description: Echo a message for testing.
            permissions:
              - network
              - project_context
            executor:
              kind: python
              entry_point: executor:run
            tools:
              - name: safe_echo
                description: Echo a message.
                parameters:
                  message:
                    type: string
                    description: Message to echo.
            """
        ).strip(),
        encoding="utf-8",
    )

    preview = load_skill_manifest(skill_dir, source="local")

    assert preview.name == "safe-echo"
    assert preview.version == "1.2.0"
    assert preview.source_type == "local"
    assert preview.permissions == ["network", "project_context"]
    assert preview.risk_level == "medium"
    assert preview.requires_confirmation is False
    assert preview.manifest_hash
    assert preview.tool_defs[0]["function"]["name"] == "safe_echo"
    assert preview.runtime_spec["manifest_hash"] == preview.manifest_hash


def test_load_agentforge_skill_manifest_rejects_unknown_permission(tmp_path):
    skill_dir = tmp_path / "unsafe"
    skill_dir.mkdir()
    (skill_dir / "agentforge-skill.yaml").write_text(
        textwrap.dedent(
            """
            name: unsafe
            version: 1.0.0
            description: Invalid permission.
            permissions:
              - root_access
            tools:
              - name: unsafe_tool
                description: Invalid tool.
                parameters: {}
            """
        ).strip(),
        encoding="utf-8",
    )

    with pytest.raises(SkillManifestError, match="permission"):
        load_skill_manifest(skill_dir, source="local")


def test_load_agentforge_skill_manifest_rejects_invalid_yaml(tmp_path):
    skill_dir = tmp_path / "broken"
    skill_dir.mkdir()
    (skill_dir / "agentforge-skill.yaml").write_text(
        "name: broken\npermissions:\n  - network\n  - [unterminated\n",
        encoding="utf-8",
    )

    with pytest.raises(SkillManifestError, match="invalid YAML"):
        load_skill_manifest(skill_dir, source="local")


def test_load_agentforge_skill_manifest_rejects_missing_manifest(tmp_path):
    skill_dir = tmp_path / "missing"
    skill_dir.mkdir()

    with pytest.raises(SkillManifestError, match="manifest"):
        load_skill_manifest(skill_dir, source="local")
