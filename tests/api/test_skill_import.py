from __future__ import annotations

import textwrap

import pytest
from sqlalchemy import select

from agent_forge.models import Skill, SkillInstall
from agent_forge.skills.registry import get_skill_registry


def _write_skill(
    root,
    *,
    name: str = "safe-echo",
    permissions: list[str] | None = None,
    tool_name: str = "safe_echo",
) -> str:
    skill_dir = root / name
    skill_dir.mkdir()
    permission_lines = "\n".join(f"  - {permission}" for permission in (permissions or ["network"]))
    (skill_dir / "agentforge-skill.yaml").write_text(
        (
            f"name: {name}\n"
            "version: 1.0.0\n"
            "description: Echo a message.\n"
            "permissions:\n"
            f"{permission_lines}\n"
            "executor:\n"
            "  kind: python\n"
            "  entry_point: executor:run\n"
            "tools:\n"
            f"  - name: {tool_name}\n"
            "    description: Echo a message.\n"
            "    parameters:\n"
            "      message:\n"
            "        type: string\n"
            "        description: Message to echo.\n"
        ),
        encoding="utf-8",
    )
    (skill_dir / "executor.py").write_text(
        textwrap.dedent(
            """
            async def run(message: str):
                return {"echo": message}
            """
        ).strip(),
        encoding="utf-8",
    )
    return str(skill_dir)


@pytest.mark.asyncio
async def test_skill_import_preview_shows_permissions_and_risk(async_client, tmp_path):
    source = _write_skill(tmp_path, permissions=["network", "project_context"])

    response = async_client.post("/api/v1/skills/import/preview", json={"source": source})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "safe-echo"
    assert body["source_type"] == "local"
    assert body["permissions"] == ["network", "project_context"]
    assert body["risk_level"] == "medium"
    assert body["requires_confirmation"] is False
    assert body["tools"][0]["name"] == "safe_echo"
    assert body["manifest_hash"]


@pytest.mark.asyncio
async def test_skill_import_install_registers_runtime_spec_and_install_metadata(
    async_client,
    db_session,
    monkeypatch,
    tmp_path,
):
    from agent_forge.skills import installer as installer_module

    monkeypatch.setattr(installer_module, "SKILLS_INSTALLED_DIR", tmp_path / "installed")
    source = _write_skill(tmp_path, permissions=["network"], tool_name="safe_echo")

    response = async_client.post("/api/v1/skills/import/install", json={"source": source})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "done"
    assert body["skill_name"] == "safe-echo"

    skill_result = await db_session.execute(select(Skill).where(Skill.name == "safe-echo"))
    skill = skill_result.scalar_one()
    assert skill.manifest_hash == body["manifest_hash"]
    assert skill.permissions == ["network"]
    assert skill.runtime_spec["manifest_hash"] == body["manifest_hash"]

    install_result = await db_session.execute(
        select(SkillInstall).where(SkillInstall.id == body["install_id"])
    )
    install = install_result.scalar_one()
    assert install.manifest_hash == body["manifest_hash"]
    assert install.permissions == ["network"]

    registry = get_skill_registry()
    assert "safe-echo" in registry.list_registered()
    assert registry.get_executor("safe_echo") is not None
    registry.unregister("safe-echo")


@pytest.mark.asyncio
async def test_skill_import_install_requires_confirmation_for_high_risk_permission(
    async_client,
    tmp_path,
):
    source = _write_skill(tmp_path, name="shell-skill", permissions=["shell"], tool_name="shell_tool")

    preview_response = async_client.post("/api/v1/skills/import/preview", json={"source": source})
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["risk_level"] == "high"
    assert preview["requires_confirmation"] is True

    install_response = async_client.post("/api/v1/skills/import/install", json={"source": source})

    assert install_response.status_code == 409
    detail = install_response.json()["detail"]
    assert detail["code"] == "SKILL_PERMISSION_CONFIRMATION_REQUIRED"
    assert detail["preview"]["permissions"] == ["shell"]


@pytest.mark.asyncio
async def test_legacy_skill_install_endpoint_requires_confirmation_for_high_risk_permission(
    async_client,
    tmp_path,
):
    source = _write_skill(tmp_path, name="legacy-shell-skill", permissions=["shell"], tool_name="legacy_shell_tool")

    install_response = async_client.post("/api/v1/skills/install", json={"source": source})

    assert install_response.status_code == 409
    detail = install_response.json()["detail"]
    assert detail["code"] == "SKILL_PERMISSION_CONFIRMATION_REQUIRED"
    assert detail["preview"]["name"] == "legacy-shell-skill"
