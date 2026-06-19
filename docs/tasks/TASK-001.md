# TASK-001：项目基础设施 & 认证系统

## 关联需求

| 用户故事 | 描述 |
|---------|------|
| US-5 | 作为全栈开发者，我想看到安全的 API 调用记录，以便审计和合规 |

> 本任务是所有功能的地基，无直接用户故事，但支撑全部 US 的运行。

## 优先级

**P1** — 必须最先完成，后续所有任务依赖它

## 验收标准

- [ ] `docker compose up -d` 能启动 PostgreSQL + RabbitMQ + Redis，健康检查全部通过
- [ ] `alembic upgrade head` 能创建全部 9 张数据表
- [ ] `GET /health` 返回三个依赖服务的连通状态
- [ ] 注册 → 登录 → 获取 access_token → 刷新 → 退出 完整流程可走通
- [ ] 未登录请求受保护接口返回 401
- [ ] 超出限流阈值返回 429 + `Retry-After` Header
- [ ] 每个请求日志中含唯一 `trace_id`

## 技术子项

### 基础设施

- [ ] **pyproject.toml + 目录结构**
  - 包名：`agent_forge`
  - 依赖：fastapi、sqlalchemy[asyncio]、alembic、pydantic-settings、aio-pika、litellm、tenacity、pybreaker、slowapi、asyncpg、bcrypt、python-jose[cryptography]
  - 开发依赖：pytest、pytest-asyncio、httpx、ruff、mypy

- [ ] **docker-compose.yml**
  - PostgreSQL 15-alpine（healthcheck: pg_isready）
  - RabbitMQ 3.13-management（healthcheck: rabbitmq-diagnostics ping）
  - Redis 7-alpine（healthcheck: redis-cli ping）
  - `.env.example` 完整模板

- [ ] **SQLAlchemy 数据库模型**（`src/agent_forge/models/`）
  - User、APIKey、Task、SubTask、TaskExecution
  - Agent、Skill、MemoryEntry、AuditLog
  - 参考：`docs/tech-design/DATABASE.md`

- [ ] **Alembic 初始迁移**
  - `alembic init migrations/`
  - 初始 revision 覆盖全部 9 张表

### FastAPI 主入口

- [ ] **main.py + 中间件**
  - trace_id 注入（每请求生成 UUID，写入 logging context）
  - CORS（读取 `CORS_ORIGINS` 环境变量）
  - `GET /health`（返回 db/rabbitmq/redis 各自状态）

### 认证模块（`src/api/routes/auth.py`）

- [ ] `POST /api/v1/auth/register`
  - bcrypt 密码哈希（12 轮）
  - 默认权限 `["read"]`
  - 重复用户名/邮箱返回 409

- [ ] `POST /api/v1/auth/login`
  - 验证密码，生成 access_token（1h）
  - refresh_token 写 HttpOnly Cookie（7d，SameSite=Strict）
  - 响应 body 含 `user.permissions`

- [ ] `POST /api/v1/auth/refresh`
  - 从 Cookie 读 refresh_token（`withCredentials`）
  - 返回新 access_token

- [ ] `POST /api/v1/auth/logout`
  - 清除 refresh_token Cookie

- [ ] **JWT 工具**（`src/agent_forge/auth/jwt.py`）
  - 生成/校验 access_token 和 refresh_token
  - 依赖注入：`get_current_user`（校验 Bearer Token）

### 限流中间件（`src/middleware/rate_limit.py`）

- [ ] slowapi + Redis 计数器
- [ ] 路由规则：`/auth/*` 10/min、`/tasks` 100/min、`/tasks/{id}` 300/min、`/skills/*` 50/min、`/dashboard` 60/min
- [ ] 超限响应：429 + `Retry-After`

## 产出物

- `pyproject.toml`
- `docker-compose.yml` + `.env.example`
- `src/agent_forge/models/*.py`
- `migrations/`（Alembic）
- `src/api/main.py`
- `src/api/routes/auth.py`
- `src/agent_forge/auth/jwt.py`
- `src/middleware/rate_limit.py`

## 参考文档

- `docs/tech-design/DATABASE.md`
- `docs/tech-design/SECURITY.md`
- `docs/tech-design/API-SPEC.md` 第 2 节
- `docs/tech-design/DEPLOYMENT.md` 第 3 节
