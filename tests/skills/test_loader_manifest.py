from __future__ import annotations

import pytest
from sqlalchemy import select

from agent_forge.models import Skill
from agent_forge.skills.loader import SkillLoader


@pytest.mark.asyncio
async def test_skill_loader_scans_agentforge_skill_yaml(db_session, tmp_path):
    skill_dir = tmp_path / "market" / "loader-yaml-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "agentforge-skill.yaml").write_text(
        "\n".join(
            [
                "name: loader-yaml-skill",
                "version: 1.0.0",
                "description: Loaded from yaml manifest.",
                "permissions:",
                "  - network",
                "tools:",
                "  - name: loader_yaml_tool",
                "    description: Loader test tool.",
                "    parameters: {}",
            ]
        ),
        encoding="utf-8",
    )

    loaded = await SkillLoader(str(tmp_path)).load_all(db_session)

    assert loaded == ["loader-yaml-skill"]
    result = await db_session.execute(select(Skill).where(Skill.name == "loader-yaml-skill"))
    skill = result.scalar_one()
    assert skill.manifest_hash
    assert skill.permissions == ["network"]
    assert skill.runtime_spec["tool_defs"][0]["function"]["name"] == "loader_yaml_tool"
