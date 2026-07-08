# 部署指南 (DEPLOYMENT.md)

## 1. 环境概览

| 环境 | 说明 | 启动方式 |
|------|------|---------|
| 本地开发 | 单机，含所有依赖 | `docker-compose up` + 手动启动后端/前端 |
| 生产 | 单机或多节点，Nginx 反向代理 | `docker-compose -f docker-compose.prod.yml up -d` |

---

## 2. 依赖服务

| 服务 | 版本 | 用途 | 默认端口 |
|------|------|------|---------|
| PostgreSQL | 15-alpine | 主数据库 | 5432 |
| RabbitMQ | 3.13-management | 消息队列（Agent 协商总线） | 5672 / 15672（管理界面） |
| Redis | 7-alpine | Skill 安装状态缓存、限流计数器 | 6379 |

---

## 3. 本地开发环境

> 本文档侧重生产部署和架构配置。本地开发环境完整操作步骤见 `docs/standards/DEVELOPMENT-GUIDE.md`。

### 3.1 前提条件

- Docker Desktop >= 4.x
- Python 3.11+
- Node.js 20+
- `uv`（Python 包管理，可用 pip 替代）

> **注意**：完整的 `docker compose` → `alembic` → `uvicorn` → `npm run dev` 操作链见 `docs/standards/DEVELOPMENT-GUIDE.md`。
> 本节保留 `docker-compose.yml` 和 `.env` 配置参考，便于快速查看端口和变量。

### 3.2 docker-compose.yml（完整配置）

```yaml
version: "3.9"

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: agentforge
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: agent_dev_pass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agent -d agentforge"]
      interval: 5s
      timeout: 3s
      retries: 10

  rabbitmq:
    image: rabbitmq:3.13-management
    environment:
      RABBITMQ_DEFAULT_USER: agent
      RABBITMQ_DEFAULT_PASS: agent_dev_pass
      RABBITMQ_DEFAULT_VHOST: agentforge
    ports:
      - "5672:5672"
      - "15672:15672"   # 管理界面：http://localhost:15672
    volumes:
      - rabbitmqdata:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
  rabbitmqdata:
  redisdata:
```

### 3.3 .env 完整模板

```bash
# ── 数据库 ──────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://agent:agent_dev_pass@localhost:5432/agentforge

# ── RabbitMQ ────────────────────────────────────
RABBITMQ_URL=amqp://agent:agent_dev_pass@localhost:5672/agentforge

# ── Redis ───────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── JWT ─────────────────────────────────────────
JWT_SECRET=dev-secret-change-in-production-32chars+
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_SEC=3600
REFRESH_TOKEN_EXPIRE_SEC=604800

# ── 服务端凭据加密 ──────────────────────────────
CREDENTIAL_ENCRYPTION_KEY=dev-credential-key-change-in-production

# ── LLM API Keys ────────────────────────────────
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
# GEMINI_API_KEY=xxx

# ── GitHub OAuth Mount ──────────────────────────
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=
GITHUB_OAUTH_REDIRECT_URI=
GITHUB_OAUTH_SCOPES=repo

# ── Skill 安装目录 ───────────────────────────────
SKILL_INSTALL_DIR=/opt/agentforge/skills

# ── CORS ────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000

# ── 应用 ────────────────────────────────────────
APP_ENV=development
LOG_LEVEL=INFO
```

### 3.4 服务端口速查

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5432 | 主数据库 |
| RabbitMQ | 5672 / 15672（管理界面） | 消息队列 |
| Redis | 6379 | 缓存 + 限流计数器 |
| 后端 API | 8000 | Swagger UI: http://localhost:8000/docs |
| 前端 | 3000 | Vue 3 开发服务器 |

---

> **本地开发操作链**（`docker compose` → `alembic` → `uvicorn` → `npm run dev` → 验证）的完整步骤见 `docs/standards/DEVELOPMENT-GUIDE.md`。

---

## 5. 生产环境部署

### 5.1 docker-compose.prod.yml

```yaml
version: "3.9"

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped
    # 生产环境不暴露端口，仅内部网络访问

  rabbitmq:
    image: rabbitmq:3.13-management
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASS}
      RABBITMQ_DEFAULT_VHOST: agentforge
    volumes:
      - rabbitmqdata:/var/lib/rabbitmq
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redisdata:/data
    restart: unless-stopped

  backend:
    build: .
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - RABBITMQ_URL=amqp://${RABBITMQ_USER}:${RABBITMQ_PASS}@rabbitmq:5672/agentforge
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CORS_ORIGINS=http://localhost:8080
    depends_on:
      db:        { condition: service_healthy }
      rabbitmq:  { condition: service_healthy }
      redis:     { condition: service_healthy }
    restart: unless-stopped
    command: >
      sh -c "alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4"

  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./web/dist:/usr/share/nginx/html:ro
      - ./certs:/etc/nginx/certs:ro   # SSL 证书
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  pgdata:
  rabbitmqdata:
  redisdata:
```

### 5.2 Nginx 配置 (nginx.conf)

```nginx
events { worker_connections 1024; }

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile on;
    gzip on;
    gzip_types text/plain text/css application/javascript application/json;

    # 限流：每 IP 每秒 20 请求
    limit_req_zone $binary_remote_addr zone=api:10m rate=20r/s;

    upstream backend {
        server backend:8000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;   # HTTP → HTTPS
    }

    server {
        listen 443 ssl;
        server_name _;

        ssl_certificate     /etc/nginx/certs/cert.pem;
        ssl_certificate_key /etc/nginx/certs/key.pem;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        # 安全 Header
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-Frame-Options DENY always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;

        # 前端静态资源
        root /usr/share/nginx/html;
        index index.html;
        location / {
            try_files $uri $uri/ /index.html;   # Vue Router history 模式
        }

        # API 反向代理
        location /api/ {
            limit_req zone=api burst=50 nodelay;
            proxy_pass         http://backend;
            proxy_http_version 1.1;
            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
        }

        # SSE 长连接特殊配置
        location /api/v1/tasks/*/stream {
            proxy_pass             http://backend;
            proxy_http_version     1.1;
            proxy_set_header       Connection '';
            proxy_buffering        off;
            proxy_cache            off;
            proxy_read_timeout     3600s;   # SSE 需要长超时
            proxy_set_header       X-Real-IP $remote_addr;
            add_header             X-Accel-Buffering no;
        }
    }
}
```

### 5.3 生产环境变量

生产环境通过 `.env.prod` 或系统环境变量注入（不提交到 Git）：

```bash
# 必填
JWT_SECRET=<32 位以上随机字符串>
POSTGRES_DB=agentforge
POSTGRES_USER=<生产用户名>
POSTGRES_PASSWORD=<强密码>
RABBITMQ_USER=<生产用户名>
RABBITMQ_PASS=<强密码>
REDIS_PASSWORD=<强密码>
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
CREDENTIAL_ENCRYPTION_KEY=<独立随机字符串，建议 32 位以上>
GITHUB_OAUTH_CLIENT_ID=<GitHub OAuth App Client ID>
GITHUB_OAUTH_CLIENT_SECRET=<GitHub OAuth App Client Secret>
GITHUB_OAUTH_REDIRECT_URI=
GITHUB_OAUTH_SCOPES=repo
```

`GITHUB_OAUTH_REDIRECT_URI` 可留空，Project 创建向导会按当前项目传入 `/api/v1/projects/{project_id}/mounts/github/oauth/callback`。无前端场景才需要配置固定回调地址。

### 5.4 前端构建

```bash
cd web
npm run build   # 输出到 dist/，由 Nginx 服务
```

### 5.5 生产启动命令

```bash
# 首次启动
docker-compose -f docker-compose.prod.yml up -d

# 更新部署
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --no-deps backend nginx
```

---

## 6. 数据库迁移管理

```bash
# 创建新迁移
alembic revision --autogenerate -m "add skill install log field"

# 执行迁移
alembic upgrade head

# 回滚一步
alembic downgrade -1

# 查看迁移历史
alembic history
```

---

## 7. 日志与监控

### 7.1 日志配置

后端日志输出到 stdout（Docker 容器收集），格式为 JSON：

```json
{
  "timestamp": "2026-06-17T10:00:00Z",
  "level": "INFO",
  "trace_id": "trace-001",
  "user_id": "user-001",
  "message": "task created",
  "task_id": "task-001"
}
```

### 7.2 健康检查

```http
GET /health
```

**响应 200**:
```json
{
  "status": "ok",
  "db": "ok",
  "rabbitmq": "ok",
  "redis": "ok"
}
```

任一依赖不健康时返回 503。

### 7.3 可观测性扩展（可选）

| 工具 | 用途 | 配置方式 |
|------|------|---------|
| Prometheus | 指标采集（请求数、延迟、成本） | 后端暴露 `/metrics` 端点 |
| Grafana | 可视化仪表盘 | 连接 Prometheus 数据源 |
| Loki | 日志聚合 | Docker 日志 driver → Loki |

> 可观测性为可选扩展，MVP 阶段不强制要求。
