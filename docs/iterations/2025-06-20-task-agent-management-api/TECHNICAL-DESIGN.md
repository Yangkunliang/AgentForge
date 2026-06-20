# TASK-002 技术设计文档

## 系统架构

### 整体架构
AgentForge 采用分层架构设计：
- **API 层**：FastAPI 路由和控制器
- **业务逻辑层**：服务和业务逻辑
- **数据访问层**：SQLAlchemy ORM
- **基础设施层**：数据库、认证、中间件

### 技术栈
- **Web 框架**：FastAPI 0.104+
- **ORM**：SQLAlchemy 2.0+（async）
- **数据库**：SQLite（开发）/ PostgreSQL（生产）
- **认证**：JWT（PyJWT）
- **数据验证**：Pydantic V2
- **测试框架**：Pytest + pytest-asyncio

## 数据库设计

### Task 表

```sql
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority VARCHAR(20) NOT NULL,
    trace_id VARCHAR(36) NOT NULL,
    result TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
```

### Agent 表

```sql
CREATE TABLE agents (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    capabilities JSON NOT NULL DEFAULT '[]',
    model VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    description VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_name ON agents(name);
```

## API 设计

### RESTful 约定
- 使用标准 HTTP 方法（GET、POST、PATCH、DELETE）
- 使用资源导向的 URL 设计
- 使用适当的 HTTP 状态码
- 统一的错误响应格式

### 任务管理 API

#### 创建任务
```
POST /api/v1/tasks
Authorization: Bearer {token}
Content-Type: application/json

{
  "description": "Implement user authentication",
  "priority": "high"
}

Response: 201 Created
{
  "id": "task-uuid",
  "description": "Implement user authentication",
  "status": "pending",
  "priority": "high",
  "trace_id": "trace-uuid",
  "result": null,
  "created_at": "2025-06-20T00:00:00Z",
  "completed_at": null,
  "sub_tasks": []
}
```

#### 查询任务列表
```
GET /api/v1/tasks?page=1&per_page=20&status=pending&priority=high
Authorization: Bearer {token}

Response: 200 OK
{
  "total": 100,
  "page": 1,
  "per_page": 20,
  "items": [...]
}
```

#### 查询任务详情
```
GET /api/v1/tasks/{task_id}
Authorization: Bearer {token}

Response: 200 OK
{
  "id": "task-uuid",
  "description": "...",
  "status": "completed",
  "priority": "high",
  "trace_id": "trace-uuid",
  "result": "Task result",
  "created_at": "2025-06-20T00:00:00Z",
  "completed_at": "2025-06-20T01:00:00Z",
  "sub_tasks": [...]
}
```

#### 取消任务
```
POST /api/v1/tasks/{task_id}/cancel
Authorization: Bearer {token}

Response: 200 OK
{
  "id": "task-uuid",
  "status": "cancelled",
  ...
}
```

#### 提交任务反馈
```
POST /api/v1/tasks/{task_id}/feedback
Authorization: Bearer {token}
Content-Type: application/json

{
  "thumbs": "up",
  "rating": 5,
  "comment": "Great work!"
}

Response: 200 OK
{
  "message": "Feedback submitted successfully"
}
```

### Agent 管理 API

#### 创建 Agent
```
POST /api/v1/agents
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "code-reviewer",
  "capabilities": ["code_review", "security_check"],
  "model": "gpt-4",
  "description": "Code review agent"
}

Response: 201 Created
{
  "id": "agent-uuid",
  "name": "code-reviewer",
  "capabilities": ["code_review", "security_check"],
  "model": "gpt-4",
  "status": "active",
  "description": "Code review agent",
  "created_at": "2025-06-20T00:00:00Z",
  "updated_at": "2025-06-20T00:00:00Z"
}
```

#### 查询 Agent 列表
```
GET /api/v1/agents?capability=code_review&status=active
Authorization: Bearer {token}

Response: 200 OK
[
  {
    "id": "agent-uuid",
    "name": "code-reviewer",
    "capabilities": ["code_review", "security_check"],
    "model": "gpt-4",
    "status": "active",
    "description": "Code review agent",
    "created_at": "2025-06-20T00:00:00Z",
    "updated_at": "2025-06-20T00:00:00Z"
  }
]
```

## 认证和授权

### 认证机制
- 使用 JWT Bearer Token 认证
- Token 包含用户 ID 和权限信息
- Token 有效期：24 小时

### 权限模型
```python
class Permission(str, PyEnum):
    READ = "read"        # 读取权限
    WRITE = "write"      # 写入权限
    ADMIN = "admin"      # 管理员权限
```

### 权限要求
- 任务管理：需要认证（任何权限）
- Agent 查询：需要 read 权限
- Agent 创建/更新/删除：需要 admin 权限

### 实现方式
```python
# 依赖注入装饰器
@router.post("")
async def create_task(
    body: TaskCreateRequest,
    current_user: User = Depends(get_current_user),  # 需要认证
) -> Task:
    ...

@router.post("")
async def create_agent(
    body: AgentCreateRequest,
    current_user: User = Depends(require_permission("admin")),  # 需要 admin 权限
) -> Agent:
    ...
```

## 异常处理

### 统一错误响应格式
```json
{
  "detail": "Error message"
}
```

### HTTP 状态码使用
- `200 OK`：请求成功
- `201 Created`：资源创建成功
- `204 No Content`：删除成功
- `400 Bad Request`：请求参数错误
- `401 Unauthorized`：未认证
- `403 Forbidden`：权限不足
- `404 Not Found`：资源不存在
- `409 Conflict`：资源冲突（如名称重复）
- `422 Unprocessable Entity`：数据验证失败
- `500 Internal Server Error`：服务器错误

## 性能优化

### 数据库查询优化
1. **索引使用**：
   - 为常用查询字段创建索引（user_id、status、priority）
   - 为外键创建索引

2. **关系加载优化**：
   - 使用 `selectinload` 预加载关系，避免 N+1 查询
   - 在 async 上下文中避免懒加载

3. **分页查询**：
   - 使用 `LIMIT` 和 `OFFSET` 实现分页
   - 限制每页最大数量（100）

### 缓存策略
- 暂未实现缓存，后续可考虑使用 Redis 缓存热点数据

## 测试策略

### 单元测试
- 使用 pytest + pytest-asyncio
- 测试覆盖所有 API 端点
- 测试正常流程和异常情况
- 测试权限控制

### 测试隔离
- 使用 SQLite 内存数据库进行测试
- 每个 test session 创建一次数据库结构
- 使用 fixture 管理测试数据

### 测试覆盖目标
- API 端点覆盖率：100%
- 业务逻辑覆盖率：> 80%

## 安全考虑

### 数据安全
1. **SQL 注入防护**：使用 ORM 参数化查询
2. **XSS 防护**：输入验证和输出编码
3. **CSRF 防护**：使用 JWT 认证

### 访问控制
1. **认证**：所有 API（除登录）需要认证
2. **授权**：基于权限的访问控制
3. **数据隔离**：用户只能访问自己的任务

### 敏感信息保护
1. **密码**：使用 bcrypt 哈希存储
2. **Token**：使用 JWT 签名，防止篡改
3. **日志**：不记录敏感信息

## 部署考虑

### 环境变量
```bash
DATABASE_URL=postgresql://user:pass@localhost/agentforge
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### 数据库迁移
- 使用 Alembic 进行数据库迁移
- 迁移脚本版本控制

### 监控和日志
- 结构化日志输出
- 关键操作日志记录
- 错误追踪和告警

## 未来扩展

### 计划中的功能
1. **任务执行引擎**：实际执行任务的逻辑
2. **Agent 协作**：多 Agent 协作完成任务
3. **任务调度**：定时任务和优先级调度
4. **实时通知**：任务状态变更通知
5. **性能监控**：API 性能指标收集

### 可扩展性设计
1. **微服务化**：可将任务管理和 Agent 管理拆分为独立服务
2. **消息队列**：使用 RabbitMQ/Redis 实现异步任务处理
3. **分布式追踪**：集成 OpenTelemetry 实现分布式追踪
4. **API 网关**：使用 API 网关统一管理和路由

## 技术债务

### 已知问题
1. 测试数据库使用文件存储，可能存在数据残留
2. 暂未实现 API 限流
3. 暂未实现请求日志记录

### 改进计划
1. 使用数据库事务回滚实现测试隔离
2. 集成 slowapi 实现 API 限流
3. 添加请求/响应中间件记录日志
4. 完善 API 文档（Swagger/OpenAPI）