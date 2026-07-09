"""LLM Provider / Model / Credential / Route API tests."""

from __future__ import annotations

import uuid


def test_llm_settings_api_creates_route_and_never_returns_plain_secret(async_client):
    suffix = "api" + uuid.uuid4().hex[:8]
    provider_key = f"anthropic-{suffix}"
    model_key = f"anthropic/claude-3-5-sonnet-{suffix}"
    route_key = f"default-{suffix}"
    provider_resp = async_client.post(
        "/api/v1/llm/providers",
        json={
            "provider_key": provider_key,
            "name": "Anthropic",
            "base_url": "https://api.anthropic.com",
            "status": "active",
        },
    )
    assert provider_resp.status_code == 201
    provider = provider_resp.json()

    model_resp = async_client.post(
        "/api/v1/llm/models",
        json={
            "provider_id": provider["id"],
            "model_key": model_key,
            "name": "Claude 3.5 Sonnet",
            "capabilities": ["text", "code"],
            "context_window": 200000,
            "input_price_per_1m": 3.0,
            "output_price_per_1m": 15.0,
            "status": "active",
        },
    )
    assert model_resp.status_code == 201
    model = model_resp.json()

    credential_resp = async_client.post(
        "/api/v1/llm/credentials",
        json={
            "provider_id": provider["id"],
            "name": "prod-key",
            "secret": "sk-ant-secret-1234",
            "active": True,
        },
    )
    assert credential_resp.status_code == 201
    credential = credential_resp.json()
    assert credential["secret_set"] is True
    assert credential["masked_secret"] == "sk-a...1234"
    assert "sk-ant-secret-1234" not in credential_resp.text

    route_resp = async_client.post(
        "/api/v1/llm/routes",
        json={
            "route_key": route_key,
            "name": "Default Route",
            "provider_id": provider["id"],
            "model_id": model["id"],
            "credential_id": credential["id"],
            "temperature": 0.2,
            "max_tokens": 8192,
            "timeout_seconds": 45,
            "fallback_route_keys": [],
            "active": True,
        },
    )
    assert route_resp.status_code == 201
    route = route_resp.json()
    assert route["route_key"] == route_key
    assert route["model_name"] == model_key

    list_resp = async_client.get("/api/v1/llm/routes")
    assert list_resp.status_code == 200
    assert "sk-ant-secret-1234" not in list_resp.text
    routes = list_resp.json()["items"]
    assert any(item["route_key"] == route_key for item in routes)

    legacy_resp = async_client.get("/api/v1/llm")
    assert legacy_resp.status_code == 200
    assert "routes" in legacy_resp.json()
    assert "sk-ant-secret-1234" not in legacy_resp.text
