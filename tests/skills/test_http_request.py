"""HTTP Request Skill 单元测试"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from agent_forge.skills.http_request import HTTP_REQUEST_TOOL, http_request, _check_url_allowed


class TestHTTPRequestToolDefinition:
    """HTTP_REQUEST_TOOL 定义测试"""

    def test_tool_definition_exists(self):
        assert HTTP_REQUEST_TOOL is not None
        assert HTTP_REQUEST_TOOL["type"] == "function"
        assert HTTP_REQUEST_TOOL["function"]["name"] == "http_request"
        assert HTTP_REQUEST_TOOL["function"]["parameters"]["required"] == ["url"]

    def test_tool_parameters(self):
        params = HTTP_REQUEST_TOOL["function"]["parameters"]["properties"]
        assert "url" in params
        assert "method" in params
        assert "headers" in params
        assert "params" in params
        assert "body" in params
        assert "timeout" in params


class TestURLSecurityCheck:
    """URL 安全校验测试"""

    def test_allowed_http_url(self):
        allowed, reason = _check_url_allowed("http://example.com/api")
        assert allowed is True
        assert reason == ""

    def test_allowed_https_url(self):
        allowed, reason = _check_url_allowed("https://api.example.com/v1/users")
        assert allowed is True
        assert reason == ""

    def test_blocked_localhost(self):
        allowed, reason = _check_url_allowed("http://localhost:8000")
        assert allowed is False
        assert "内网地址" in reason

    def test_blocked_127(self):
        allowed, reason = _check_url_allowed("http://127.0.0.1:5000")
        assert allowed is False
        assert "内网地址" in reason

    def test_blocked_192_168(self):
        allowed, reason = _check_url_allowed("http://192.168.1.100:8080")
        assert allowed is False
        assert "内网地址" in reason

    def test_blocked_10_network(self):
        allowed, reason = _check_url_allowed("http://10.0.0.1:3000")
        assert allowed is False
        assert "内网地址" in reason

    def test_invalid_url_scheme(self):
        allowed, reason = _check_url_allowed("ftp://example.com/file.txt")
        assert allowed is False
        assert "不支持的协议" in reason

    def test_invalid_url_format(self):
        allowed, reason = _check_url_allowed("not-a-url")
        assert allowed is False
        assert "不支持的协议" in reason


@pytest.mark.asyncio
class TestHTTPRequestExecution:
    """HTTP 请求执行测试"""

    async def test_get_request_success(self):
        result = await http_request("https://httpbin.org/get")
        assert "status_code" in result
        assert result["status_code"] == 200
        assert result["ok"] is True
        assert "body" in result

    async def test_post_request_success(self):
        result = await http_request(
            "https://httpbin.org/post",
            method="POST",
            body={"key": "value"},
        )
        assert result["status_code"] == 200
        assert result["ok"] is True

    async def test_request_with_params(self):
        result = await http_request(
            "https://httpbin.org/get",
            params={"foo": "bar", "count": "10"},
        )
        assert result["status_code"] == 200

    async def test_request_timeout(self):
        result = await http_request(
            "https://httpbin.org/delay/10",
            timeout=1,
        )
        assert "error" in result
        assert "超时" in result["error"]

    async def test_request_connect_error(self):
        result = await http_request(
            "http://nonexistent-domain-12345.invalid/",
            timeout=2,
        )
        assert "error" in result

    async def test_localhost_blocked(self):
        result = await http_request("http://localhost:8000")
        assert "error" in result
        assert "内网地址" in result["error"]