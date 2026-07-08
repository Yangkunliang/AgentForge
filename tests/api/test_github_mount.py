"""GitHub OAuth Mount API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.models import AuditLog, OAuthCredential, ProjectMount, User
from agent_forge.security.credentials import decrypt_secret
from middleware.auth import get_current_user


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


async def test_github_oauth_start_creates_state_and_audit(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from api.routes import projects as project_routes

    monkeypatch.setattr(project_routes.settings, "github_oauth_client_id", "gh-client")
    monkeypatch.setattr(project_routes.settings, "github_oauth_redirect_uri", "http://testserver/github/callback")

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "GitHub 项目"},
        headers=_auth_headers(fake_user),
    ).json()

    resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/start",
        json={"repo_full_name": "acme/shop-api", "role": "primary"},
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 201
    payload = resp.json()
    assert payload["state"]
    assert "github.com/login/oauth/authorize" in payload["authorization_url"]
    assert "gh-client" in payload["authorization_url"]
    assert "acme/shop-api" not in payload["authorization_url"]

    audit_rows = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource == "github_mount",
                AuditLog.action == "github_mount.oauth.started",
            )
        )
    ).scalars().all()
    assert audit_rows
    assert audit_rows[-1].details["repo_full_name"] == "acme/shop-api"
    assert "access_token" not in str(audit_rows[-1].details)


async def test_github_oauth_start_rejects_untrusted_redirect_uri(
    async_client: TestClient,
    fake_user: User,
    monkeypatch,
):
    from api.routes import projects as project_routes

    monkeypatch.setattr(project_routes.settings, "github_oauth_client_id", "gh-client")

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "GitHub 项目"},
        headers=_auth_headers(fake_user),
    ).json()

    resp = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/start",
        json={
            "repo_full_name": "acme/shop-api",
            "redirect_uri": "https://example.com/oauth/callback",
        },
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "GitHub OAuth redirect URI is not allowed"


async def test_github_oauth_callback_creates_mount_without_exposing_token(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from api.routes import projects as project_routes

    monkeypatch.setattr(project_routes.settings, "github_oauth_client_id", "gh-client")
    monkeypatch.setattr(project_routes.settings, "github_oauth_client_secret", "gh-secret")
    monkeypatch.setattr(project_routes.settings, "github_oauth_redirect_uri", "http://testserver/github/callback")

    async def fake_exchange_github_oauth_code(code: str, redirect_uri: str):
        assert code == "oauth-code"
        assert redirect_uri == "http://testserver/github/callback"
        return {"access_token": "gho_super_secret", "scopes": ["repo"]}

    async def fake_fetch_github_repo(access_token: str, repo_full_name: str):
        assert access_token == "gho_super_secret"
        assert repo_full_name == "acme/shop-api"
        return {
            "owner": "acme",
            "name": "shop-api",
            "full_name": "acme/shop-api",
            "default_branch": "main",
            "html_url": "https://github.com/acme/shop-api",
        }

    monkeypatch.setattr(project_routes, "exchange_github_oauth_code", fake_exchange_github_oauth_code)
    monkeypatch.setattr(project_routes, "fetch_github_repo", fake_fetch_github_repo)

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "GitHub 项目"},
        headers=_auth_headers(fake_user),
    ).json()
    start = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/start",
        json={"repo_full_name": "acme/shop-api", "role": "primary"},
        headers=_auth_headers(fake_user),
    ).json()

    resp = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/callback",
        params={"code": "oauth-code", "state": start["state"]},
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 201
    mount = resp.json()
    assert mount["mount_type"] == "github"
    assert mount["status"] == "connected"
    assert mount["locator"] == "github://acme/shop-api"
    assert mount["metadata"]["repo_full_name"] == "acme/shop-api"
    assert mount["metadata"]["default_branch"] == "main"
    assert mount["metadata"]["credential_id"]
    assert "access_token" not in str(mount)
    assert "gho_super_secret" not in str(mount)

    credential = (
        await db_session.execute(
            select(OAuthCredential).where(OAuthCredential.id == mount["metadata"]["credential_id"])
        )
    ).scalar_one()
    assert credential.encrypted_access_token != "gho_super_secret"
    assert decrypt_secret(credential.encrypted_access_token) == "gho_super_secret"
    assert credential.scopes_json == ["repo"]

    db_mount = (
        await db_session.execute(select(ProjectMount).where(ProjectMount.id == mount["id"]))
    ).scalar_one()
    assert db_mount.metadata_json["credential_id"] == credential.id


async def test_github_oauth_callback_accepts_browser_redirect_without_auth_header(
    async_client: TestClient,
    fake_user: User,
    monkeypatch,
):
    from api.main import app
    from api.routes import projects as project_routes

    monkeypatch.setattr(project_routes.settings, "github_oauth_client_id", "gh-client")
    monkeypatch.setattr(project_routes.settings, "github_oauth_client_secret", "gh-secret")
    monkeypatch.setattr(project_routes.settings, "github_oauth_redirect_uri", "http://testserver/github/callback")

    async def fake_exchange_github_oauth_code(code: str, redirect_uri: str):
        return {"access_token": "gho_super_secret", "scopes": ["repo"]}

    async def fake_fetch_github_repo(access_token: str, repo_full_name: str):
        return {
            "owner": "acme",
            "name": "shop-api",
            "full_name": "acme/shop-api",
            "default_branch": "main",
            "html_url": "https://github.com/acme/shop-api",
        }

    monkeypatch.setattr(project_routes, "exchange_github_oauth_code", fake_exchange_github_oauth_code)
    monkeypatch.setattr(project_routes, "fetch_github_repo", fake_fetch_github_repo)

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "GitHub 项目"},
        headers=_auth_headers(fake_user),
    ).json()
    start = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/start",
        json={"repo_full_name": "acme/shop-api"},
        headers=_auth_headers(fake_user),
    ).json()

    auth_override = app.dependency_overrides.pop(get_current_user, None)
    try:
        resp = async_client.get(
            f"/api/v1/projects/{project['id']}/mounts/github/oauth/callback",
            params={"code": "oauth-code", "state": start["state"]},
        )
    finally:
        if auth_override is not None:
            app.dependency_overrides[get_current_user] = auth_override

    assert resp.status_code == 201
    assert resp.json()["metadata"]["repo_full_name"] == "acme/shop-api"


async def test_github_oauth_callback_rejects_reused_state(
    async_client: TestClient,
    fake_user: User,
    monkeypatch,
):
    from api.routes import projects as project_routes

    monkeypatch.setattr(project_routes.settings, "github_oauth_client_id", "gh-client")
    monkeypatch.setattr(project_routes.settings, "github_oauth_client_secret", "gh-secret")
    monkeypatch.setattr(project_routes.settings, "github_oauth_redirect_uri", "http://testserver/github/callback")

    async def fake_exchange_github_oauth_code(code: str, redirect_uri: str):
        return {"access_token": "gho_super_secret", "scopes": ["repo"]}

    async def fake_fetch_github_repo(access_token: str, repo_full_name: str):
        return {
            "owner": "acme",
            "name": "shop-api",
            "full_name": "acme/shop-api",
            "default_branch": "main",
            "html_url": "https://github.com/acme/shop-api",
        }

    monkeypatch.setattr(project_routes, "exchange_github_oauth_code", fake_exchange_github_oauth_code)
    monkeypatch.setattr(project_routes, "fetch_github_repo", fake_fetch_github_repo)

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "GitHub 项目"},
        headers=_auth_headers(fake_user),
    ).json()
    start = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/start",
        json={"repo_full_name": "acme/shop-api"},
        headers=_auth_headers(fake_user),
    ).json()

    first = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/callback",
        params={"code": "oauth-code", "state": start["state"]},
        headers=_auth_headers(fake_user),
    )
    second = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/callback",
        params={"code": "oauth-code", "state": start["state"]},
        headers=_auth_headers(fake_user),
    )

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["detail"] == "OAuth state is invalid or expired"


async def test_delete_github_mount_revokes_credential_and_writes_audit(
    async_client: TestClient,
    fake_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from api.routes import projects as project_routes

    monkeypatch.setattr(project_routes.settings, "github_oauth_client_id", "gh-client")
    monkeypatch.setattr(project_routes.settings, "github_oauth_client_secret", "gh-secret")
    monkeypatch.setattr(project_routes.settings, "github_oauth_redirect_uri", "http://testserver/github/callback")

    async def fake_exchange_github_oauth_code(code: str, redirect_uri: str):
        return {"access_token": "gho_super_secret", "scopes": ["repo"]}

    async def fake_fetch_github_repo(access_token: str, repo_full_name: str):
        return {
            "owner": "acme",
            "name": "shop-api",
            "full_name": "acme/shop-api",
            "default_branch": "main",
            "html_url": "https://github.com/acme/shop-api",
        }

    monkeypatch.setattr(project_routes, "exchange_github_oauth_code", fake_exchange_github_oauth_code)
    monkeypatch.setattr(project_routes, "fetch_github_repo", fake_fetch_github_repo)

    project = async_client.post(
        "/api/v1/projects",
        json={"name": "GitHub 项目"},
        headers=_auth_headers(fake_user),
    ).json()
    start = async_client.post(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/start",
        json={"repo_full_name": "acme/shop-api"},
        headers=_auth_headers(fake_user),
    ).json()
    mount = async_client.get(
        f"/api/v1/projects/{project['id']}/mounts/github/oauth/callback",
        params={"code": "oauth-code", "state": start["state"]},
        headers=_auth_headers(fake_user),
    ).json()

    resp = async_client.delete(
        f"/api/v1/projects/{project['id']}/mounts/{mount['id']}",
        headers=_auth_headers(fake_user),
    )

    assert resp.status_code == 204
    credential = (
        await db_session.execute(
            select(OAuthCredential).where(OAuthCredential.id == mount["metadata"]["credential_id"])
        )
    ).scalar_one()
    assert credential.revoked_at is not None

    audit_rows = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource == "github_mount",
                AuditLog.action == "github_mount.revoked",
            )
        )
    ).scalars().all()
    assert audit_rows
    assert audit_rows[-1].details["mount_id"] == mount["id"]
    assert audit_rows[-1].details["credential_id"] == credential.id
