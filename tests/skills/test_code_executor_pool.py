"""Code executor sandbox pool lifecycle tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_forge.skills import code_executor


@pytest.mark.asyncio
async def test_init_sandbox_pool_skips_prewarm_by_default(monkeypatch):
    def fail_get_pool():
        raise AssertionError("_get_pool should not run when prewarm is disabled")

    monkeypatch.setattr(
        code_executor,
        "sandbox_settings",
        SimpleNamespace(sandbox_pool_prewarm_enabled=False),
    )
    monkeypatch.setattr(code_executor, "_get_pool", fail_get_pool)

    warmed = await code_executor.init_sandbox_pool()

    assert warmed is False


@pytest.mark.asyncio
async def test_init_sandbox_pool_bootstraps_when_enabled(monkeypatch):
    calls: list[str] = []

    class FakePool:
        async def bootstrap(self):
            calls.append("bootstrap")

    monkeypatch.setattr(
        code_executor,
        "sandbox_settings",
        SimpleNamespace(sandbox_pool_prewarm_enabled=True),
    )
    monkeypatch.setattr(code_executor, "_get_pool", lambda: FakePool())

    warmed = await code_executor.init_sandbox_pool()

    assert warmed is True
    assert calls == ["bootstrap"]
