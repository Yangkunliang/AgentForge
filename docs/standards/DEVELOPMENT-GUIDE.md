# 开发指南

本文档说明 AgentForge 项目的环境配置、启动步骤和测试方法。

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | ≥ 3.11 |
| Docker | ≥ 24.0 |
| Docker Compose | ≥ 2.20 |

## 快速启动

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd AgentForge

# 安装 Python 依赖（包含开发依赖）
pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 根据需要修改 .env 中的配置
# 主要配置项：
# - DATABASE_URL：数据库连接地址
# - JWT_SECRET_KEY：JWT 密钥（生产环境必须修改）
# - CORS_ORIGINS：允许的前端域名
```

### 3. 启动 Docker 容器

```bash
# 启动 PostgreSQL + RabbitMQ + Redis
docker compose up -d

# 查看容器状态
docker compose ps

# 等待健康检查通过（约 10-30 秒）
# 状态应显示为 "healthy"
```

### 4. 运行数据库迁移

```bash
# 创建数据库表
alembic upgrade head

# 验证迁移状态
alembic current
```

### 5. 启动 FastAPI 服务

```bash
# 开发模式（自动重载）
PYTHONPATH=src uvicorn src.api.main:app --reload --port 8000

# 生产模式
PYTHONPATH=src uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 6. 验证服务

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 预期响应
{
  "status": "ok",
  "db": "ok",
  "rabbitmq": "ok",
  "redis": "ok"
}
```

## API 文档

启动服务后访问：

| 文档类型 | 地址 |
|----------|------|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

## 测试

### 运行测试套件

```bash
# 运行所有测试
pytest tests/ -v

# 运行指定模块测试
pytest tests/api/test_auth.py -v
pytest tests/api/test_health.py -v

# 运行并显示覆盖率
pytest tests/ -v --cov=src --cov-report=html

# 覆盖率报告生成在 htmlcov/index.html
```

### 测试数据库说明

- pytest 测试默认使用 SQLite 文件数据库（`test_db.sqlite`）
- 不依赖 Docker 容器即可运行基础 API 测试
- 测试完成后自动清理临时数据库文件

### 手动测试认证流程

```bash
# 1. 注册用户
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "TestPass123"}'

# 2. 登录获取 token（会保存 refresh_token 到 cookie）
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=testuser" \
  -d "password=TestPass123" \
  -c cookies.txt

# 3. 刷新 token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -b cookies.txt

# 4. 退出登录
curl -X POST http://localhost:8000/api/v1/auth/logout
```

## 开发规范

### Pre-commit Hooks

```bash
# 安装 pre-commit hooks
pre-commit install

# 手动运行检查
pre-commit run --all-files
```

每次 `git commit` 会自动执行：
- `ruff check`：代码 lint
- `ruff format --check`：格式化检查
- `mypy --strict`：类型检查

### 代码风格

| 工具 | 配置文件 | 说明 |
|------|----------|------|
| Ruff | `pyproject.toml` | Lint + 格式化 |
| MyPy | `pyproject.toml` | 严格类型检查 |

```bash
# 格式化代码
ruff format src/ tests/

# Lint 检查
ruff check src/ tests/

# 类型检查
mypy src/
```

## 常见问题

### Docker 容器启动失败

```bash
# 查看容器日志
docker compose logs postgres
docker compose logs rabbitmq
docker compose logs redis

# 重启容器
docker compose restart
```

### 数据库迁移失败

```bash
# 查看当前迁移状态
alembic current

# 回滚到上一版本
alembic downgrade -1

# 重新迁移
alembic upgrade head
```

### 测试失败

```bash
# 清理测试缓存
pytest --cache-clear

# 删除测试数据库
rm -f test_db.sqlite

# 重新运行测试
pytest tests/ -v
```

## 目录结构

```
AgentForge/
├── src/
│   ├── agent_forge/     # 核心业务逻辑
│   │   ├── models/      # SQLAlchemy 数据模型
│   │   ├── auth/        # JWT 认证模块
│   │   ├── config.py    # 配置管理
│   │   └── database.py  # 数据库连接
│   ├── api/
│   │   ├── main.py      # FastAPI 主入口
│   │   └── routes/      # API 路由
│   └── middleware/      # 中间件
├── tests/
│   ├── conftest.py      # pytest fixtures
│   └── api/             # API 测试
├── migrations/          # Alembic 迁移文件
├── docker-compose.yml   # Docker 容器配置
├── pyproject.toml       # 项目配置
└── .env.example         # 环境变量模板
```

## 相关文档

- [API 规范](../tech-design/API-SPEC.md)
- [数据库设计](../tech-design/DATABASE.md)
- [安全设计](../tech-design/SECURITY.md)
- [部署指南](../tech-design/DEPLOYMENT.md)