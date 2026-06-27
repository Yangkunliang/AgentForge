"""全局分布式 Trace 系统

设计目标
--------
- 零侵入：用 @span 装饰器自动采集函数耗时，业务代码不需要手动打日志
- 请求级隔离：用 contextvars 做 trace context，不同并发请求互不干扰
- 嵌套 span：支持 caller → callee 的父子关系，自动记录调用层级
- 结构化输出：每个 span 输出 JSON 行，便于 grep / 日志平台消费
- 轻量：纯标准库 + Python 装饰器，无需 Jaeger / Zipkin 等外部依赖

trace_id 生命周期
-----------------
一次"发送消息"对应唯一一个 trace_id，贯穿整条链路：

  ┌─ HTTP POST /sessions/.../chat ─────────────────────────────────┐
  │  TraceMiddleware: start_request_trace(trace_id=X-Request-Id)   │
  │  send_message():                                               │
  │    trace_id = get_trace_id()   # 读当前 context 的 trace_id   │
  │    asyncio.create_task(                                        │
  │      _run_task_with_skills(trace_id=trace_id, ...)             │
  │    )                   ↑ 显式透传，不依赖 context 复制         │
  └────────────────────────┼───────────────────────────────────────┘
                           │
  ┌─ Background Task ───────┼──────────────────────────────────────┐
  │  _run_task_with_skills: │                                      │
  │    start_task_trace(trace_id=trace_id)  # 重建同一个 trace     │
  │    所有 @span 子调用自动归属同一 trace_id                       │
  └────────────────────────────────────────────────────────────────┘

为什么不能直接依赖 asyncio.create_task 的 context 复制？
  asyncio.create_task 确实会复制父 Task 的 contextvars snapshot，
  但 TraceMiddleware 用 contextmanager + token.reset() 在请求结束后
  清空了 _current_trace。由于 create_task 发生在 middleware 的
  yield 之前（handler 内），理论上此时 context 还有值，可以复制。
  但这个时序依赖脆弱（middleware 顺序、异常路径均可能破坏），
  因此选择显式透传 trace_id + 在后台任务里重建 context，
  行为确定、不依赖隐式复制。

使用方式
--------
1. 函数级自动 span（推荐）：

    from agent_forge.tracing import span

    @span("llm.tool_use_complete")
    async def tool_use_complete(self, messages, tools, config): ...

    @span()   # 不传名称时自动用 module.function_name
    async def my_func(): ...

2. 代码块级手动 span：

    from agent_forge.tracing import get_tracer

    async with get_tracer().start_span("db.query") as s:
        result = await db.execute(...)
        s.set_tag("rows", len(result))

3. 任意位置读取当前 trace_id：

    from agent_forge.tracing import get_trace_id
    logger.info("processing trace=%s", get_trace_id())

输出格式（每行一个 JSON）
--------------------------
{
  "ts": "2026-06-27T07:00:01.123Z",
  "trace_id": "2c2dcdf3-...",       # 整条请求链路唯一
  "span_id": "a1b2c3d4",
  "parent_id": "e5f6a7b8",          # 根 span 时为 null
  "name": "llm.tool_use_complete",
  "duration_ms": 3241,
  "status": "ok",                   # ok | error
  "tags": {"model": "deepseek-v3", "tools": 5, "tokens": 412},
  "error": null                     # 异常时为 "ExceptionType: message"
}

超过 3s 的 span 自动用 WARNING 级别输出，便于快速发现慢操作：
  grep WARNING app.log | grep SPAN
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("agent_forge.trace")


# ── Trace / Span 数据结构 ────────────────────────────────────────

@dataclass
class _SpanContext:
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    start_time: float
    tags: dict[str, Any] = field(default_factory=dict)

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.start_time) * 1000)


@dataclass
class _TraceContext:
    trace_id: str
    span_stack: list[_SpanContext] = field(default_factory=list)

    @property
    def current_span(self) -> _SpanContext | None:
        return self.span_stack[-1] if self.span_stack else None


# contextvars：每个 asyncio Task 独立一个 context 副本
_current_trace: ContextVar[_TraceContext | None] = ContextVar(
    "_current_trace", default=None
)


# ── 对外 API ────────────────────────────────────────────────────

def get_trace_id() -> str | None:
    """获取当前请求/任务的 trace_id，无 trace context 时返回 None"""
    ctx = _current_trace.get()
    return ctx.trace_id if ctx else None


def get_current_span() -> _SpanContext | None:
    ctx = _current_trace.get()
    return ctx.current_span if ctx else None


# ── Tracer ──────────────────────────────────────────────────────

class Tracer:

    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        tags: dict[str, Any] | None = None,
    ) -> AsyncGenerator[_SpanContext, None]:
        """异步 span context manager。

        Example::
            async with get_tracer().start_span("db.query", tags={"table": "users"}) as s:
                rows = await db.execute(...)
                s.tags["rows"] = len(rows)
        """
        ctx = _current_trace.get()
        if ctx is None:
            # 无 trace context（测试或非 HTTP 路径），静默执行
            sp = _SpanContext(
                trace_id="no-trace", span_id=_short_id(),
                parent_id=None, name=name,
                start_time=time.monotonic(), tags=dict(tags or {}),
            )
            yield sp
            return

        parent_id = ctx.current_span.span_id if ctx.current_span else None
        sp = _SpanContext(
            trace_id=ctx.trace_id, span_id=_short_id(),
            parent_id=parent_id, name=name,
            start_time=time.monotonic(), tags=dict(tags or {}),
        )
        ctx.span_stack.append(sp)
        error_str: str | None = None
        try:
            yield sp
        except Exception as exc:
            error_str = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            ctx.span_stack.pop()
            _emit_span(sp, error=error_str)

    @contextmanager
    def start_span_sync(self, name: str, tags: dict[str, Any] | None = None):
        """同步 span context manager（用于同步函数）"""
        ctx = _current_trace.get()
        if ctx is None:
            sp = _SpanContext(
                trace_id="no-trace", span_id=_short_id(),
                parent_id=None, name=name,
                start_time=time.monotonic(), tags=dict(tags or {}),
            )
            yield sp
            return

        parent_id = ctx.current_span.span_id if ctx.current_span else None
        sp = _SpanContext(
            trace_id=ctx.trace_id, span_id=_short_id(),
            parent_id=parent_id, name=name,
            start_time=time.monotonic(), tags=dict(tags or {}),
        )
        ctx.span_stack.append(sp)
        error_str: str | None = None
        try:
            yield sp
        except Exception as exc:
            error_str = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            ctx.span_stack.pop()
            _emit_span(sp, error=error_str)


_tracer = Tracer()


def get_tracer() -> Tracer:
    return _tracer


# ── @span 装饰器 ─────────────────────────────────────────────────

def span(
    name: str | None = None,
    tags: dict[str, Any] | None = None,
    tag_args: list[str] | None = None,
):
    """将函数自动包装为一个 trace span。

    Args:
        name:     span 名称，默认 "module.function_name"
        tags:     静态 tag dict
        tag_args: 从函数参数中提取 tag 的参数名列表

    Examples::

        @span("llm.complete")
        async def complete(self, prompt, config): ...

        @span(tag_args=["model"])
        async def chat_complete(self, messages, model="gpt-4"): ...

        @span()   # 自动命名
        def sync_helper(): ...
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__.split('.')[-1]}.{func.__name__}"
        is_async = asyncio.iscoroutinefunction(func)
        sig = inspect.signature(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                extra_tags = dict(tags or {})
                if tag_args:
                    bound = sig.bind_partial(*args, **kwargs)
                    bound.apply_defaults()
                    for arg_name in tag_args:
                        if arg_name in bound.arguments:
                            extra_tags[arg_name] = _safe_tag(bound.arguments[arg_name])
                async with get_tracer().start_span(span_name, tags=extra_tags):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                extra_tags = dict(tags or {})
                if tag_args:
                    bound = sig.bind_partial(*args, **kwargs)
                    bound.apply_defaults()
                    for arg_name in tag_args:
                        if arg_name in bound.arguments:
                            extra_tags[arg_name] = _safe_tag(bound.arguments[arg_name])
                with get_tracer().start_span_sync(span_name, tags=extra_tags):
                    return func(*args, **kwargs)
            return sync_wrapper

    # 支持无参调用：@span 而非 @span()
    if callable(name):
        func, name = name, None
        return decorator(func)

    return decorator


# ── Trace Context 生命周期 ────────────────────────────────────────

@contextmanager
def start_request_trace(trace_id: str | None = None):
    """HTTP 请求级 trace context（在 TraceMiddleware 里调用）。

    trace_id 优先使用请求头 X-Request-Id，否则自动生成。
    """
    tid = trace_id or str(uuid.uuid4())
    ctx = _TraceContext(trace_id=tid)
    token = _current_trace.set(ctx)
    try:
        yield tid
    finally:
        _current_trace.reset(token)


@contextmanager
def start_task_trace(trace_id: str | None = None):
    """后台 asyncio Task 级 trace context。

    在 _run_task_with_skills 等后台任务入口调用，
    trace_id 由调用方从 HTTP 请求 context 中读取后透传，
    保证整条链路（HTTP + 后台任务）共用同一个 trace_id。

    为什么不直接依赖 asyncio.create_task 的 context 复制：
      TraceMiddleware 用 contextmanager + token.reset() 管理 context，
      create_task 的复制时序与 middleware yield/reset 的边界关系脆弱，
      显式透传 trace_id 后在此重建 context 更可靠。
    """
    tid = trace_id or str(uuid.uuid4())
    ctx = _TraceContext(trace_id=tid)
    token = _current_trace.set(ctx)
    try:
        yield tid
    finally:
        _current_trace.reset(token)


# ── Span 输出 ────────────────────────────────────────────────────

def _emit_span(sp: _SpanContext, error: str | None = None) -> None:
    """将 span 序列化为结构化 JSON 日志行。"""
    duration_ms = sp.elapsed_ms()
    record = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "trace_id": sp.trace_id,
        "span_id": sp.span_id,
        "parent_id": sp.parent_id,
        "name": sp.name,
        "duration_ms": duration_ms,
        "status": "error" if error else "ok",
        "tags": sp.tags or None,
        "error": error,
    }
    line = json.dumps(record, ensure_ascii=False, default=str)

    if error:
        logger.error("[SPAN] %s", line)
    elif duration_ms > 3000:
        # 超过 3s 自动升为 WARNING，便于快速发现慢操作
        logger.warning("[SPAN] %s", line)
    else:
        logger.info("[SPAN] %s", line)


# ── 工具函数 ─────────────────────────────────────────────────────

def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _safe_tag(val: Any) -> Any:
    """将函数参数转为安全的 tag 值，避免大对象写入 tag。"""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        return val if len(val) <= 100 else val[:100] + "..."
    if isinstance(val, (list, tuple)):
        return len(val)
    if isinstance(val, dict):
        return len(val)
    if val is None:
        return None
    return type(val).__name__
