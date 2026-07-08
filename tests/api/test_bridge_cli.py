"""Agent Bridge CLI tests."""

from __future__ import annotations

from agent_forge.cli import build_mount_payload


def test_build_mount_payload_resolves_local_root(tmp_path):
    root = tmp_path / "shop-api"
    root.mkdir()

    payload = build_mount_payload(root, display_name=None, role="primary")

    assert payload["mount_type"] == "local"
    assert payload["display_name"] == "shop-api"
    assert payload["locator"] == str(root.resolve())
    assert payload["role"] == "primary"
    assert payload["status"] == "connected"
    assert payload["metadata"]["root_path"] == str(root.resolve())
    assert payload["metadata"]["bridge"] == "agentforge-cli"
