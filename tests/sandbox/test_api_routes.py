"""
tests/sandbox/test_api_routes.py
=================================
沙箱 REST API 路由集成测试（FastAPI TestClient）

覆盖端点
--------
- POST /api/v1/sandboxes — 创建沙箱
- POST /api/v1/sandboxes/{id}/execute — 执行代码
- POST /api/v1/sandboxes/{id}/files/read — 读取文件
- POST /api/v1/sandboxes/{id}/files/write — 写入文件
- POST /api/v1/sandboxes/{id}/pause — 暂停
- POST /api/v1/sandboxes/{id}/resume — 恢复
- POST /api/v1/sandboxes/{id}/destroy — 销毁
- GET /api/v1/sandboxes — 列出沙箱
"""

import pytest
from fastapi.testclient import TestClient

from agent_forge.sandbox.base import SandboxDestroyedError
from agent_forge.sandbox.mock import MockSandboxExecutor
from agent_forge.sandbox.manager import SandboxManager

# 导入路由模块以注册路由
from api.routes import sandboxes  # noqa: F401

# ── 夹具 ─────────────────────────────────────────────────────────────


@pytest.fixture
def manager():
    """返回一个干净的 SandboxManager 并替换全局单例。"""
    mgr = SandboxManager(MockSandboxExecutor(), ttl_seconds=300)
    old = sandboxes._global_sandbox
    sandboxes._global_sandbox = mgr
    yield mgr
    # 清理
    sandboxes._global_sandbox = old


@pytest.fixture
def client(manager):
    """FastAPI TestClient"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(sandboxes.router)
    return TestClient(app)


# ── 基础路由测试 ──────────────────────────────────────────────────────


def test_create_sandbox(client):
    resp = client.post("/api/v1/sandboxes")
    assert resp.status_code == 200
    data = resp.json()
    assert "sandbox_id" in data
    assert data["status"] == "running"


def test_list_sandboxes_empty(client):
    resp = client.get("/api/v1/sandboxes")
    assert resp.status_code == 200
    assert resp.json() == {"sandboxes": []}


def test_list_sandboxes_with_active(client):
    client.post("/api/v1/sandboxes")
    resp = client.get("/api/v1/sandboxes")
    assert resp.status_code == 200
    assert len(resp.json()["sandboxes"]) == 1


def test_execute_code(client):
    create_resp = client.post("/api/v1/sandboxes")
    sandbox_id = create_resp.json()["sandbox_id"]

    resp = client.post(
        f"/api/v1/sandboxes/{sandbox_id}/execute",
        params={"code": "print(42)"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "42" in data["stdout"]


def test_execute_code_inline(client):
    """使用路径参数中的 sandbox_id 执行"""
    create_resp = client.post("/api/v1/sandboxes")
    sandbox_id = create_resp.json()["sandbox_id"]

    resp = client.post(
        f"/api/v1/sandboxes/{sandbox_id}/execute?code=print('inline')&timeout=5",
    )
    assert resp.status_code == 200


def test_files_write(client):
    create_resp = client.post("/api/v1/sandboxes")
    sandbox_id = create_resp.json()["sandbox_id"]

    resp = client.post(
        f"/api/v1/sandboxes/{sandbox_id}/files/write",
        json={"path": "/tmp/test.txt", "content": "hello file"},
    )
    assert resp.status_code == 200


def test_files_read(client):
    create_resp = client.post("/api/v1/sandboxes")
    sandbox_id = create_resp.json()["sandbox_id"]

    client.post(
        f"/api/v1/sandboxes/{sandbox_id}/files/write",
        json={"path": "/tmp/hello.txt", "content": "world"},
    )
    resp = client.post(
        f"/api/v1/sandboxes/{sandbox_id}/files/read",
        json={"path": "/tmp/hello.txt"},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "world"


def test_pause_sandbox(client):
    create_resp = client.post("/api/v1/sandboxes")
    sandbox_id = create_resp.json()["sandbox_id"]

    resp = client.post(f"/api/v1/sandboxes/{sandbox_id}/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_resume_sandbox(client):
    create_resp = client.post("/api/v1/sandboxes")
    sandbox_id = create_resp.json()["sandbox_id"]

    client.post(f"/api/v1/sandboxes/{sandbox_id}/pause")
    resp = client.post(f"/api/v1/sandboxes/{sandbox_id}/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_destroy_sandbox(client):
    create_resp = client.post("/api/v1/sandboxes")
    sandbox_id = create_resp.json()["sandbox_id"]

    resp = client.post(f"/api/v1/sandboxes/{sandbox_id}/destroy")
    assert resp.status_code == 200
    assert resp.json()["status"] == "destroyed"


def test_execute_on_destroyed_returns_410(client):
    create_resp = client.post("/api/v1/sandboxes")
    sandbox_id = create_resp.json()["sandbox_id"]

    client.post(f"/api/v1/sandboxes/{sandbox_id}/destroy")

    resp = client.post(
        f"/api/v1/sandboxes/{sandbox_id}/execute",
        json={"code": "print('hi')"},
    )
    assert resp.status_code == 410
    assert resp.json()["error"] == "destroyed"
