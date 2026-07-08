"""FastAPI 主入口"""

from __future__ import annotations

# 必须在所有 import 之前加载 .env，确保 os.environ 包含所有配置
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from agent_forge.config import settings
from middleware.rate_limit import limiter as middleware_limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
)
logger = logging.getLogger("agent_forge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgentForge starting up...")

    # ── 0. 安全检查：JWT Secret Key 必须配置 ──────────────────────────
    if not settings.jwt_secret_key:
        logger.error(
            "FATAL: JWT_SECRET_KEY is not set. "
            "Please set the environment variable or add to .env. "
            "The default 'change-me-in-production' has been removed."
        )
        raise RuntimeError(
            "JWT_SECRET_KEY must be set in production. "
            "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    elif settings.jwt_secret_key == "change-me-in-production":
        logger.error(
            "FATAL: JWT_SECRET_KEY still uses the default placeholder value. "
            "Generate a strong key with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
        raise RuntimeError("JWT_SECRET_KEY uses the default placeholder value.")

    # ── 1. 预热 LLM Provider（避免首次请求时 import litellm 阻塞 6s）────
    try:
        from agent_forge.llm.provider import get_llm_provider
        provider = get_llm_provider()
        logger.info("LLM provider warmed up: available=%s", getattr(provider, "is_available", True))
    except Exception as e:
        logger.warning("LLM provider warmup failed (non-fatal): %s", e)

    # ── 2. 注册内置 Skills ────────────────────────────────────────────
    try:
        from agent_forge.skills.builtin import register_builtin_skills
        await register_builtin_skills()
        logger.info("Built-in skills initialized")
    except Exception as e:
        logger.warning("Built-in skill registration failed (non-fatal): %s", e)

    # ── 3. 预热 SkillRegistry（加载工具定义）─────────────────────────
    try:
        from agent_forge.skills.registry import get_skill_registry
        registry = get_skill_registry()
        tools = registry.get_all_tool_defs()
        logger.info("SkillRegistry warmed up: %d tools", len(tools))
    except Exception as e:
        logger.warning("SkillRegistry warmup failed (non-fatal): %s", e)

    # ── 4. 启动 MCP Server 连接池 ─────────────────────────────────────
    try:
        from agent_forge.mcp.client import get_mcp_pool
        from agent_forge.mcp.config import load_mcp_configs
        mcp_pool = get_mcp_pool()
        mcp_configs = load_mcp_configs()
        await mcp_pool.start_all(mcp_configs)
        if mcp_pool.active_servers:
            logger.info("MCP servers started: %s", mcp_pool.active_servers)
        else:
            logger.info("No MCP servers configured")
    except Exception as e:
        logger.warning("MCP server initialization failed (non-fatal): %s", e)

    # ── 5. 启动沙箱 TTL 回收器 ───────────────────────────────────────
    reclaimer = None
    try:
        from agent_forge.config import sandbox_settings
        from agent_forge.sandbox.reclaimer import SandboxReclaimer
        reclaimer = SandboxReclaimer(
            interval=sandbox_settings.cube_sandbox_reclaim_interval,
            pause_ttl=sandbox_settings.cube_sandbox_pause_ttl,
        )
        await reclaimer.start()
        logger.info("SandboxReclaimer started (interval=%ds)", sandbox_settings.cube_sandbox_reclaim_interval)
    except Exception as e:
        logger.warning("SandboxReclaimer startup failed (non-fatal): %s", e)

    # ── 6. 预热沙箱池 ────────────────────────────────────────────────
    try:
        from agent_forge.skills.code_executor import init_sandbox_pool
        await init_sandbox_pool()
        logger.info("SandboxPool warmed up")
    except Exception as e:
        logger.warning("SandboxPool warmup failed (non-fatal): %s", e)

    logger.info("AgentForge startup complete ✓")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    if reclaimer is not None:
        try:
            await reclaimer.stop()
        except Exception as e:
            logger.warning("SandboxReclaimer shutdown error: %s", e)

    try:
        from agent_forge.mcp.client import get_mcp_pool
        await get_mcp_pool().stop_all()
        logger.info("MCP servers stopped")
    except Exception as e:
        logger.warning("MCP server shutdown error: %s", e)

    # ── Shutdown: 沙箱池 ────────────────────────────────────────────
    try:
        from agent_forge.skills.code_executor import shutdown_sandbox_pool
        await shutdown_sandbox_pool()
        logger.info("SandboxPool shut down")
    except Exception as e:
        logger.warning("SandboxPool shutdown error: %s", e)

    logger.info("AgentForge shutting down...")


app = FastAPI(
    title="AgentForge",
    description="通用多智能体协同框架",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = middleware_limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
        headers={"Retry-After": "60"},
    )


# ── 中间件（后注册先执行）────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "X-API-Key", "X-Request-Id", "X-Trace-Id", "Content-Type"],
)

from middleware.trace import TraceMiddleware  # noqa: E402
app.add_middleware(TraceMiddleware)


# ── 统一验证错误响应 ──────────────────────────────────────────

from fastapi.exceptions import RequestValidationError  # noqa: E402

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc not in ("body", "query", "path"))
        errors.append({"field": field, "issue": error["msg"]})
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "VALIDATION_ERROR", "message": "请求参数校验失败", "details": errors}},
    )


# ── 路由挂载 ──────────────────────────────────────────────────

from api.routes import agents, auth, dashboard, health, llm, memory, projects, sandboxes, sessions, skills, tasks, tools, uploads  # noqa: E402
from agent_forge.api.sse import sse_router  # noqa: E402

app.include_router(health.router,      prefix="/api/v1",           tags=["health"])
app.include_router(auth.router,        prefix="/api/v1/auth",      tags=["auth"])
app.include_router(tasks.router,       prefix="/api/v1/tasks",     tags=["tasks"])
app.include_router(agents.router,      prefix="/api/v1/agents",    tags=["agents"])
app.include_router(dashboard.router,   prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(skills.router,      prefix="/api/v1/skills",    tags=["skills"])
app.include_router(sessions.router,    prefix="/api/v1/sessions",  tags=["sessions"])
app.include_router(projects.router,    prefix="/api/v1/projects",  tags=["projects"])
app.include_router(projects.artifact_router, prefix="/api/v1/artifacts", tags=["artifacts"])
app.include_router(llm.router,         prefix="/api/v1",           tags=["llm"])
app.include_router(sse_router,         prefix="/api/v1",           tags=["sse"])
app.include_router(tools.router,       prefix="/api/v1",           tags=["tools"])
app.include_router(uploads.router,     prefix="/api/v1",           tags=["uploads"])
app.include_router(memory.router,      prefix="/api/v1/memory",    tags=["memory"])
app.include_router(sandboxes.router,   prefix="/api/v1/sandboxes", tags=["sandboxes"])
