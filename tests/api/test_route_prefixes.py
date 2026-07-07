from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import memory, sandboxes


def test_memory_router_mounts_under_api_v1_memory_without_double_api_prefix():
    app = FastAPI()
    app.include_router(memory.router, prefix="/api/v1/memory")
    client = TestClient(app)

    ok = client.post("/api/v1/memory/semantic", json={"content": "x"}).status_code
    bad = client.post("/api/v1/api/memory/semantic", json={"content": "x"}).status_code

    assert ok != 404
    assert bad == 404


def test_sandboxes_router_mounts_under_api_v1_sandboxes_without_double_prefix():
    app = FastAPI()
    app.include_router(sandboxes.router, prefix="/api/v1/sandboxes")
    client = TestClient(app)

    ok = client.get("/api/v1/sandboxes").status_code
    bad = client.get("/api/v1/api/v1/sandboxes").status_code

    assert ok != 404
    assert bad == 404
