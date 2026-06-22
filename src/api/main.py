"""FastAPI 主入口"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from agent_forge.config import settings

# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
logger = logging.getLogger("agent_forge")

# ── Limitter 初始化 ──────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("AgentForge starting up...")

    # 注册内置 Skills（web-search、weather）到 DB + SkillRegistry
    try:
        from agent_forge.skills.builtin import register_builtin_skills
        await register_builtin_skills()
        logger.info("Built-in skills initialized")
    except Exception as e:
        logger.warning("Built-in skill registration failed (non-fatal): %s", e)

    yield
    logger.info("AgentForge shutting down...")


# ── FastAPI 应用 ──────────────────────────────────────────────

app = FastAPI(
    title="AgentForge",
    description="通用多智能体协同框架",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册限流器
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """限流异常处理：返回 429 + Retry-After"""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
        headers={"Retry-After": "60"},
    )


# ── CORS 中间件 ───────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "X-API-Key", "X-Request-Id", "Content-Type"],
)


# ── Trace ID 中间件 ───────────────────────────────────────────

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next) -> Any:
    """为每个请求注入 trace_id，写入日志 context"""
    trace_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    request.state.trace_id = trace_id

    logger.info(f"{request.method} {request.url.path} trace_id={trace_id}")
    response = await call_next(request)
    response.headers["X-Request-Id"] = trace_id
    return response


# ── 统一错误响应格式 ──────────────────────────────────────────

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """统一验证错误响应格式"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc not in ("body", "query", "path"))
        errors.append({
            "field": field,
            "issue": error["msg"],
        })
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数校验失败",
                "details": errors,
            }
        },
    )


# ── 路由挂载 ──────────────────────────────────────────────────

from api.routes import agents, auth, dashboard, health, llm, sessions, skills, tasks, tools  # noqa: E402
from agent_forge.api.sse import sse_router  # noqa: E402

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(skills.router, prefix="/api/v1/skills", tags=["skills"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(llm.router, prefix="/api/v1", tags=["llm"])
app.include_router(sse_router, prefix="/api/v1", tags=["sse"])
app.include_router(  # noqa: F821
    tools.router,  # type: ignore[name-defined]
    prefix="/api/v1",
    tags=["tools"],
)
