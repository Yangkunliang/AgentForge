"""HTTP Request Skill — 发起任意 HTTP 请求

让 LLM 通过此工具调用任何 REST API，无需预先集成。

适用场景：
  - 快速访问自定义内部 API
  - 调用公开 REST 接口（汇率、IP 查询、翻译等）
  - 验证某个 URL 是否可访问

安全限制（通过 ALLOWED_HTTP_HOSTS / BLOCKED_HTTP_HOSTS 环境变量控制）：
  - 默认不限制（开发模式）
  - 生产环境建议配置白名单
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HTTP_REQUEST_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "http_request",
        "description": (
            "发起 HTTP 请求，调用任意 REST API 并返回响应内容。"
            "当需要获取实时汇率、调用特定 API 端点、验证 URL 可访问性时使用。"
            "不要猜测 API 返回值，必须调用此工具获取真实数据。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "请求目标 URL，必须包含 http:// 或 https:// 前缀",
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                    "description": "HTTP 方法，默认 GET",
                },
                "headers": {
                    "type": "object",
                    "description": "请求头 dict，如 {'Authorization': 'Bearer token'}",
                },
                "params": {
                    "type": "object",
                    "description": "URL 查询参数 dict，如 {'page': '1', 'limit': '10'}",
                },
                "body": {
                    "type": "object",
                    "description": "请求体 dict，仅 POST/PUT/PATCH 时有效，自动序列化为 JSON",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时秒数，默认 15",
                },
            },
            "required": ["url"],
        },
    },
}


# ── 安全控制 ────────────────────────────────────────────────


def _get_allowed_hosts() -> set[str]:
    raw = os.getenv("ALLOWED_HTTP_HOSTS", "")
    return {h.strip() for h in raw.split(",") if h.strip()} if raw else set()


def _get_blocked_hosts() -> set[str]:
    raw = os.getenv("BLOCKED_HTTP_HOSTS", "")
    return {h.strip() for h in raw.split(",") if h.strip()} if raw else set()


def _check_url_allowed(url: str) -> tuple[bool, str]:
    """
    校验 URL 是否允许访问。
    返回 (allowed: bool, reason: str)
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except Exception:
        return False, f"无效的 URL 格式：{url}"

    if parsed.scheme not in ("http", "https"):
        return False, f"不支持的协议：{parsed.scheme}，仅允许 http/https"

    host = parsed.hostname or ""

    # 拦截内网地址（防止 SSRF）
    _INTERNAL_PREFIXES = ("127.", "10.", "192.168.", "172.")
    if any(host.startswith(p) for p in _INTERNAL_PREFIXES) or host in ("localhost", "::1"):
        # 允许开发环境通过环境变量豁免
        if os.getenv("ALLOW_INTERNAL_HTTP", "").lower() not in ("1", "true", "yes"):
            return False, f"拒绝访问内网地址：{host}（如需开发测试，设置 ALLOW_INTERNAL_HTTP=1）"

    blocked = _get_blocked_hosts()
    if host in blocked:
        return False, f"域名 {host} 在黑名单中"

    allowed = _get_allowed_hosts()
    if allowed and host not in allowed:
        return False, f"域名 {host} 不在白名单中（ALLOWED_HTTP_HOSTS）"

    return True, ""


# ── 主函数 ──────────────────────────────────────────────────


async def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    发起 HTTP 请求，返回结构化响应。

    Returns:
        {
          "status_code": 200,
          "headers": {"content-type": "application/json", ...},
          "body": <parsed JSON 或 text 字符串>,
          "url": "https://...",
          "elapsed_ms": 123,
        }
    """
    allowed, reason = _check_url_allowed(url)
    if not allowed:
        return {"error": reason, "url": url}

    method = method.upper()
    req_headers = {
        "User-Agent": "AgentForge/1.0",
        "Accept": "application/json, text/plain, */*",
        **(headers or {}),
    }

    import time

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=req_headers,
                params=params,
                json=body if body else None,
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # 尝试解析 JSON，否则返回文本（截断超长内容）
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            try:
                body_data: Any = resp.json()
            except Exception:
                body_data = resp.text[:5000]
        else:
            body_data = resp.text[:5000]

        # 过滤响应头，只保留有意义的字段
        useful_headers = {
            k: v for k, v in resp.headers.items()
            if k.lower() in (
                "content-type", "content-length", "x-ratelimit-remaining",
                "x-request-id", "last-modified", "etag",
            )
        }

        logger.info(
            "http_request: %s %s → %d (%dms)",
            method, url, resp.status_code, elapsed_ms,
        )

        return {
            "status_code": resp.status_code,
            "ok": resp.is_success,
            "headers": useful_headers,
            "body": body_data,
            "url": str(resp.url),
            "elapsed_ms": elapsed_ms,
        }

    except httpx.TimeoutException:
        return {"error": f"请求超时（{timeout}s）", "url": url}
    except httpx.ConnectError as e:
        return {"error": f"连接失败：{e}", "url": url}
    except Exception as e:
        logger.exception("http_request failed: %s %s → %s", method, url, e)
        return {"error": f"请求失败：{e}", "url": url}
