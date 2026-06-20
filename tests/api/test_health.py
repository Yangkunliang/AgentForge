"""测试健康检查端点"""

from __future__ import annotations

import pytest


def test_health_status_200(async_client):
    """GET /health 返回 200"""
    resp = async_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "db" in data
    assert "rabbitmq" in data
    assert "redis" in data


def test_health_returns_all_fields(async_client):
    """健康检查响应包含所有依赖字段"""
    resp = async_client.get("/api/v1/health")
    data = resp.json()
    for key in ("db", "rabbitmq", "redis"):
        assert key in data, f"Missing key: {key}"
