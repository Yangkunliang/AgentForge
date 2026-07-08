"""GitHub OAuth helpers."""

from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from agent_forge.config import settings


class GitHubOAuthError(RuntimeError):
    """Raised when GitHub OAuth or repo metadata calls fail."""


@dataclass(frozen=True)
class GitHubOAuthToken:
    access_token: str
    scopes: list[str]


def build_github_authorization_url(*, state: str, redirect_uri: str) -> str:
    if not settings.github_oauth_client_id:
        raise GitHubOAuthError("GitHub OAuth client id is not configured")

    params = {
        "client_id": settings.github_oauth_client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": settings.github_oauth_scopes,
    }
    return "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)


async def exchange_github_oauth_code(code: str, redirect_uri: str) -> GitHubOAuthToken:
    if not settings.github_oauth_client_id or not settings.github_oauth_client_secret:
        raise GitHubOAuthError("GitHub OAuth client credentials are not configured")

    payload = urllib.parse.urlencode(
        {
            "client_id": settings.github_oauth_client_id,
            "client_secret": settings.github_oauth_client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://github.com/login/oauth/access_token",
        data=payload,
        headers={"Accept": "application/json"},
        method="POST",
    )

    response = await asyncio.to_thread(_read_json_request, request)
    token = response.get("access_token")
    if not token:
        raise GitHubOAuthError(response.get("error_description") or "GitHub OAuth token exchange failed")
    scopes = [scope for scope in str(response.get("scope") or settings.github_oauth_scopes).split(",") if scope]
    return GitHubOAuthToken(access_token=token, scopes=scopes)


async def fetch_github_repo(access_token: str, repo_full_name: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo_full_name}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    response = await asyncio.to_thread(_read_json_request, request)
    full_name = response.get("full_name")
    if not full_name:
        raise GitHubOAuthError("GitHub repo metadata response is invalid")
    owner = response.get("owner") or {}
    return {
        "owner": owner.get("login") or str(full_name).split("/")[0],
        "name": response.get("name") or str(full_name).split("/")[-1],
        "full_name": full_name,
        "default_branch": response.get("default_branch") or "main",
        "html_url": response.get("html_url") or f"https://github.com/{full_name}",
    }


def _read_json_request(request: urllib.request.Request) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise GitHubOAuthError(str(exc) or exc.__class__.__name__) from exc
