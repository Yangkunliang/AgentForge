"""Trace Middleware

每个 HTTP 请求自动开启 trace context：
  - 从 X-Request-Id header 读取或生成 trace_id
  - 在 contextvars 里注入 _TraceContext，作用域覆盖整个请求生命周期
  - 响应头写回 X-Request-Id，便于客户端关联日志
  - 记录请求级 span（method + path + status_code + duration_ms）
"""

from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from agent_forge.tracing import start_request_trace, get_tracer

import logging
logger = logging.getLogger("agent_forge.trace")


class TraceMiddleware(BaseHTTPMiddleware):
    """为每个 HTTP 请求注入 trace context，自动记录请求级 span"""

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = (
            request.headers.get("X-Request-Id")
            or request.headers.get("X-Trace-Id")
            or str(uuid.uuid4())
        )
        request.state.trace_id = trace_id

        # 跳过心跳和静态路径（避免日志噪音）
        skip_paths = {"/health", "/api/v1/health", "/favicon.ico"}
        if request.url.path in skip_paths:
            return await call_next(request)

        with start_request_trace(trace_id=trace_id):
            span_name = f"http.{request.method.lower()} {request.url.path}"
            async with get_tracer().start_span(
                span_name,
                tags={
                    "method": request.method,
                    "path": request.url.path,
                    "client": request.client.host if request.client else None,
                },
            ) as root_span:
                t0 = time.monotonic()
                try:
                    response = await call_next(request)
                    root_span.tags["status_code"] = response.status_code
                except Exception as exc:
                    root_span.tags["status_code"] = 500
                    raise
                finally:
                    root_span.tags["duration_ms"] = int((time.monotonic() - t0) * 1000)

        response.headers["X-Request-Id"] = trace_id
        response.headers["X-Trace-Id"] = trace_id
        return response
