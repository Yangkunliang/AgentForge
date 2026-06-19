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
  - 开发依赖：pytest、pytest-asyncio、httpx、ruff、mypy、pre-commit、coverage、pytest-cov、pytest-dotenv
  - 配置 `pyproject.toml` 中的 `[tool.pytest.ini_options]`（自动发现 `tests/**/test_*.py`，`asyncio_mode=auto`）
  - 项目根目录 `tests/conftest.py`：全局 fixture（async_client、fake_user、mock_litellm）

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

### 测试基础设施

- [ ] **pytest 配置**
  - `pyproject.toml` 中 `[tool.pytest.ini_options]`：`testpaths = ["tests"]`、`pythonpath = ["src"]`、`asyncio_mode = "auto"`
  - 根目录 `tests/conftest.py`：全局 fixture
    - `async_client`：httpx.AsyncClient (TestClient wrapper)
    - `fake_user`：工厂函数生成测试用户数据
    - `db_session`：事务回滚 fixture（每个测试后自动 rollback，不污染数据库）
    - `mock_litellm`：模拟 LLM 调用返回（避免每次测试都调 API）
  - `pytest -v --cov=src/` 能跑通基础 health 端点测试

- [ ] **API 层基础测试**（`tests/api/test_health.py`、`tests/api/test_auth.py`）
  - `GET /health` → 200 + `{"status":"ok","db":"ok",...}`
  - `POST /auth/register` → 201 + user data
  - `POST /auth/login` → 200 + access_token + refresh_token cookie
  - `POST /auth/login` with wrong password → 401
  - 受保护端点未带 token → 401
  - 受保护端点带过期 token → 401

- [ ] **Harness 层基础测试**（`tests/harness/`）
  - `test_validator_input`：非法输入被 Reject
  - `test_governance_retry`：3 次指数退避后成功
  - `test_governance_circuit_open`：连续 5 次失败后熔断器打开

### Pre-commit Hooks（`.pre-commit-config.yaml`）

- [ ] **阻塞式检查**（commit 时同步执行，必须全部通过）
  - `ruff check` — lint（< 1s）
  - `ruff format --check` — 格式化（< 1s）
  - `mypy --strict` — 类型检查（< 5s）
  - `pytest tests/ -x --timeout=30` — 只跑改动文件相关的单测（`pre-commit-hooks` 中用 `pyupgrade` + `pytest` 的 `--durations=0`，范围用 `staged-files` 过滤）
  - 配置 `.pre-commit-hooks.yaml` 或 `pre-commit` 的 `files:` 正则限制

- [ ] **`pre-commit install`** 后 `git commit` 自动触发检查

### CI 流水线（`.github/workflows/ci.yml`）

- [ ] **PR 触发**（非阻塞，评论式）
  - `on: [pull_request]` 触发全量测试 + lint + mypy
  - 失败时 **阻塞合并**（`status: success` 是 required check）
  - 单元测试覆盖率阈值：≥ 60%

- [ ] **LLM Code Review**（非阻塞，异步评论）
  - `on: [pull_request_target]` 触发
  - 调用 AgentForge 自身 /review API（或 liteLLM）对 diff 做评论
  - 评论挂在 PR 上，不阻塞合并按钮
  - 支持 `@claude review` 手动触发（issue_comment 事件）

## 产出物

- `pyproject.toml`
- `docker-compose.yml` + `.env.example`
- `src/agent_forge/models/*.py`
- `migrations/`（Alembic）
- `src/api/main.py`
- `src/api/routes/auth.py`
- `src/agent_forge/auth/jwt.py`
- `src/middleware/rate_limit.py`

### 新增产出物

- `tests/conftest.py` — 全局 pytest fixtures
- `tests/api/test_health.py`、`tests/api/test_auth.py` — API 层基础测试
- `tests/harness/test_validator.py`、`tests/harness/test_governance.py` — Harness 层基础测试
- `.pre-commit-config.yaml` — pre-commit hooks 配置
- `.github/workflows/ci.yml` — CI pipeline（测试 + lint + LLM review）
- `docs/tech-design/TESTING.md` — 测试策略设计文档

## 参考文档

- `docs/tech-design/DATABASE.md`
- `docs/tech-design/SECURITY.md`
- `docs/tech-design/API-SPEC.md` 第 2 节
- `docs/tech-design/DEPLOYMENT.md` 第 3 节
- `docs/tech-design/TESTING.md`（新增，本任务产出）
