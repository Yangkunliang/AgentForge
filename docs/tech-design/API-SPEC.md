# 多智能体协同框架 - API 规范 (API-SPEC.md)

## 1. 基础规范

- **Base URL**: `http://localhost:8000/api/v1`
- **Content-Type**: `application/json`
- **认证头**: `Authorization: Bearer <token>`
- **API Key 头**: `X-API-Key: <key>`
- **CORS**: 允许 `localhost:3000` 等前端地址

---

## 2. 认证 API

### 2.1 用户注册

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "alice",
  "email": "alice@example.com",
  "password": "StrongPass123!"
}
```

**响应 201**:
```json
{
  "user_id": "user-001",
  "username": "alice",
  "email": "alice@example.com",
  "permissions": ["read"],
  "created_at": "2026-06-17T10:00:00Z"
}
```

**说明：**
- 新注册用户默认权限为 `["read"]`，admin 权限需由管理员通过 `PATCH /api/v1/users/{id}/permissions` 赋予
- 密码要求：8 位以上，含大小写字母和数字

### 2.2 用户登录

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "alice@example.com",
  "password": "StrongPass123!"
}
```

**响应 200**:
```json
{
  "access_token": "eyJ...",
  "expires_in": 3600,
  "user": {
    "id": "user-001",
    "username": "alice",
    "permissions": ["read", "write"]
  }
}
```

**说明：**
- `refresh_token` 通过 `Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax; Path=/api/v1/auth` 写入浏览器，不在响应 body 中返回
- `access_token` 有效期 1h，`refresh_token` 有效期 7d

### 2.3 刷新 Token

```http
POST /api/v1/auth/refresh
```

**说明：** 不需要请求体，浏览器自动携带 HttpOnly Cookie 中的 `refresh_token`。

**响应 200**:
```json
{
  "access_token": "eyJ...",
  "expires_in": 3600
}
```

**错误 401**：`refresh_token` 过期或无效，需重新登录。

### 2.4 退出登录

```http
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

后端清除 `refresh_token` Cookie，响应 204。

### 2.5 生成 API Key

```http
POST /api/v1/apikeys
Authorization: Bearer <token>

{
  "name": "my-service-key",
  "permissions": ["read", "write"]
}
```

**响应 201**:
```json
{
  "key_id": "key-001",
  "name": "my-service-key",
  "api_key": "ma_live_xxxx",
  "permissions": ["read", "write"],
  "created_at": "2026-06-17T10:00:00Z"
}
```

**注意：** `api_key` 仅在创建时返回一次，后续不可查询。

---

## 3. 任务 API

### 3.1 创建任务

```http
POST /api/v1/tasks
Authorization: Bearer <token>

{
  "description": "审查这个 PR 的代码质量",
  "priority": "high",
  "expected_models": ["gpt-4", "claude-3"]
}
```

**响应 201**:
```json
{
  "task_id": "task-001",
  "status": "processing",
  "created_at": "2026-06-17T10:00:00Z",
  "trace_id": "trace-001",
  "sub_tasks": [
    { "id": "sub-001", "description": "review_style", "status": "pending" },
    { "id": "sub-002", "description": "review_logic", "status": "pending" }
  ]
}
```

### 3.2 查询任务列表

```http
GET /api/v1/tasks?page=1&per_page=20&status=completed&priority=high
Authorization: Bearer <token>
```

**响应 200**:
```json
{
  "total": 100,
  "page": 1,
  "per_page": 20,
  "items": [
    {
      "task_id": "task-001",
      "description": "审查这个 PR 的代码质量",
      "status": "completed",
      "priority": "high",
      "result": "发现 3 个问题...",
      "agents_used": ["reviewer-001"],
      "skills_used": ["code-review"],
      "total_cost_usd": 0.05,
      "created_at": "2026-06-17T10:00:00Z",
      "completed_at": "2026-06-17T10:02:00Z"
    }
  ]
}
```

### 3.3 查询单个任务

```http
GET /api/v1/tasks/{task_id}
Authorization: Bearer <token>
```

**响应 200**（含子任务详情）:
```json
{
  "task_id": "task-001",
  "description": "审查这个 PR 的代码质量",
  "status": "completed",
  "priority": "high",
  "result": "发现 3 个问题...",
  "trace_id": "trace-001",
  "sub_tasks": [
    {
      "id": "sub-001",
      "description": "review_style",
      "status": "completed",
      "assigned_agent_id": "reviewer-001",
      "result": "代码风格符合规范"
    }
  ],
  "total_cost_usd": 0.05,
  "created_at": "2026-06-17T10:00:00Z",
  "completed_at": "2026-06-17T10:02:00Z"
}
```

### 3.4 取消任务

```http
POST /api/v1/tasks/{task_id}/cancel
Authorization: Bearer <token>
```

**响应 200**:
```json
{ "task_id": "task-001", "status": "cancelled" }
```

### 3.5 提交任务反馈

```http
POST /api/v1/tasks/{task_id}/feedback
Authorization: Bearer <token>

{
  "thumbs": 1,
  "rating": 4,
  "comment": "分析得很到位"
}
```

**字段说明：**
- `thumbs`: `1`（点赞）或 `-1`（点踩）
- `rating`: 1–5 星评分（可选）
- `comment`: 文字备注（可选，最长 500 字）

**响应 200**:
```json
{ "task_id": "task-001", "feedback_recorded": true }
```

---

## 4. Agent API

### 4.1 注册 Agent

```http
POST /api/v1/agents
Authorization: Bearer <token>   (需要 admin 权限)

{
  "name": "coder-001",
  "capabilities": ["code_generation", "code_review"],
  "model": "gpt-4",
  "description": "代码生成专家"
}
```

**响应 201**:
```json
{
  "agent_id": "agent-001",
  "name": "coder-001",
  "capabilities": ["code_generation", "code_review"],
  "model": "gpt-4",
  "status": "active",
  "created_at": "2026-06-17T10:00:00Z"
}
```

### 4.2 查询 Agent 列表

```http
GET /api/v1/agents?capability=code_review&status=active
Authorization: Bearer <token>
```

### 4.3 更新 Agent

```http
PATCH /api/v1/agents/{agent_id}
Authorization: Bearer <token>   (需要 admin 权限)

{
  "status": "inactive"
}
```

### 4.4 删除 Agent

```http
DELETE /api/v1/agents/{agent_id}
Authorization: Bearer <token>   (需要 admin 权限)
```

---

## 5. Skill API

### 5.1 安装 Skill

```http
POST /api/v1/skills/install
Authorization: Bearer <token>   (需要 admin 权限)

{
  "source": "git+https://github.com/user/my-skill.git",
  "version": "1.0.0"
}
```

**响应 202**（异步，返回安装任务 ID）:
```json
{
  "install_id": "install-001",
  "skill_name": "my-skill",
  "status": "pending"
}
```

### 5.2 查询安装进度

```http
GET /api/v1/skills/install/{install_id}
Authorization: Bearer <token>
```

**响应 200**:
```json
{
  "install_id": "install-001",
  "skill_name": "my-skill",
  "status": "installing",
  "log": "Collecting my-skill\n  Downloading my_skill-1.0.0-py3-none-any.whl\nInstalling...",
  "error": null
}
```

`status` 取值：`pending` | `installing` | `done` | `failed`

### 5.3 列出已安装 Skill

```http
GET /api/v1/skills
Authorization: Bearer <token>
```

**响应 200**:
```json
{
  "total": 3,
  "items": [
    {
      "name": "code-review",
      "version": "1.0.0",
      "description": "代码质量审查",
      "entry_point": "code_review.main",
      "installed_at": "2026-06-17T10:00:00Z"
    }
  ]
}
```

### 5.4 卸载 Skill

```http
DELETE /api/v1/skills/{skill_name}
Authorization: Bearer <token>   (需要 admin 权限)
```

**响应 204**。

---

## 6. Dashboard API

```http
GET /api/v1/dashboard
Authorization: Bearer <token>
```

**响应 200**:
```json
{
  "tasks": {
    "total": 152,
    "pending": 3,
    "processing": 5,
    "completed": 140,
    "failed": 4
  },
  "agents": {
    "active": 8,
    "inactive": 2
  },
  "skills": {
    "total": 6
  },
  "cost": {
    "today_usd": 12.50,
    "trend_pct": 8.3,
    "daily_7d": [
      { "date": "2026-06-11", "usd": 9.20 },
      { "date": "2026-06-12", "usd": 11.50 },
      { "date": "2026-06-13", "usd": 8.30 },
      { "date": "2026-06-14", "usd": 14.10 },
      { "date": "2026-06-15", "usd": 10.80 },
      { "date": "2026-06-16", "usd": 11.54 },
      { "date": "2026-06-17", "usd": 12.50 }
    ]
  },
  "recent_tasks": [
    {
      "task_id": "task-152",
      "description": "审查 PR #88",
      "status": "completed",
      "total_cost_usd": 0.06,
      "created_at": "2026-06-17T10:00:00Z"
    }
  ]
}
```

**说明：** `trend_pct` 为正表示费用较昨日增加，为负表示减少。

---

## 7. 费用统计 API

```http
GET /api/v1/cost?date=2026-06-17
Authorization: Bearer <token>
```

**响应 200**:
```json
{
  "date": "2026-06-17",
  "total_cost_usd": 15.50,
  "model_costs": {
    "gpt-4": 10.20,
    "gpt-4o-mini": 3.30,
    "claude-3-sonnet": 2.00
  },
  "total_tasks": 50,
  "avg_cost_per_task": 0.31
}
```

---

## 8. SSE 流式输出

### 8.1 订阅任务事件流

```http
GET /api/v1/tasks/{task_id}/stream
Authorization: Bearer <token>
Accept: text/event-stream
Cache-Control: no-cache
```

**说明：** 使用 `fetch + ReadableStream` 订阅，不使用原生 `EventSource`（原因：`EventSource` 不支持自定义 Header）。前端实现见 FRONTEND-ARCHITECTURE.md 第 6 节。

### 8.2 事件类型

| 事件 | 说明 | data 字段 |
|------|------|----------|
| `task_started` | 任务开始处理 | `{ task_id, status }` |
| `sub_task_created` | 子任务创建 | `{ sub_task_id, description }` |
| `bid_received` | Agent 竞标到达 | `{ sub_task_id, bids: [{agent_id, confidence}] }` |
| `agent_selected` | 最佳 Agent 选定 | `{ sub_task_id, agent_id }` |
| `message` | 中间进度消息 | `{ content }` |
| `skill_called` | Skill 被调用 | `{ skill_id, input }` |
| `skill_result` | Skill 执行结果 | `{ skill_id, result }` |
| `sub_task_completed` | 子任务完成 | `{ sub_task_id, result }` |
| `task_completed` | 任务完成 | `{ task_id, result, total_cost_usd }` |
| `task_failed` | 任务失败 | `{ task_id, error }` |

### 8.3 响应示例

```
event: task_started
data: {"task_id": "task-001", "status": "processing"}

event: sub_task_created
data: {"sub_task_id": "sub-001", "description": "review_style"}

event: bid_received
data: {"sub_task_id": "sub-001", "bids": [{"agent_id": "reviewer-001", "confidence": 0.9}]}

event: agent_selected
data: {"sub_task_id": "sub-001", "agent_id": "reviewer-001"}

event: message
data: {"content": "正在分析代码风格..."}

event: skill_called
data: {"skill_id": "code-review", "input": {"code": "..."}}

event: skill_result
data: {"skill_id": "code-review", "result": "..."}

event: sub_task_completed
data: {"sub_task_id": "sub-001", "result": "代码风格符合规范"}

event: task_completed
data: {"task_id": "task-001", "result": "发现 3 个问题...", "total_cost_usd": 0.05}
```

---

## 9. Webhook 回调

### 9.1 注册 Webhook

```http
POST /api/v1/webhooks
Authorization: Bearer <token>

{
  "url": "https://myapp.com/callback",
  "events": ["task.completed", "task.failed"]
}
```

### 9.2 回调格式

```http
POST /callback
Content-Type: application/json
X-Signature: sha256=<hmac>

{
  "event": "task.completed",
  "task_id": "task-001",
  "timestamp": "2026-06-17T10:02:00Z",
  "data": { ... }
}
```

`X-Signature` 用于验签，密钥在注册 Webhook 时由后端返回。

---

## 10. 导出 API

### 10.1 发起导出

```http
POST /api/v1/exports
Authorization: Bearer <token>   (需要 admin 权限)

{
  "type": "training_data",
  "start_date": "2026-01-01",
  "end_date": "2026-06-17",
  "format": "jsonl",
  "delevel": "level_1"
}
```

**响应 202**:
```json
{
  "export_id": "export-001",
  "status": "processing",
  "total_records": 1500,
  "estimated_size_mb": 50
}
```

### 10.2 查询导出状态

```http
GET /api/v1/exports/{export_id}
Authorization: Bearer <token>
```

### 10.3 下载导出文件

```http
GET /api/v1/exports/{export_id}/download
Authorization: Bearer <token>
```

---

## 11. 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `AUTH_FAILED` | 401 | 认证失败（Token 无效或过期） |
| `REFRESH_TOKEN_EXPIRED` | 401 | refresh_token 过期，需重新登录 |
| `PERMISSION_DENIED` | 403 | 权限不足 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `AGENT_NOT_FOUND` | 404 | Agent 不存在 |
| `SKILL_NOT_FOUND` | 404 | Skill 不存在 |
| `INSTALL_NOT_FOUND` | 404 | 安装任务不存在 |
| `VALIDATION_ERROR` | 400 | 参数校验失败 |
| `DUPLICATE_USERNAME` | 409 | 用户名已存在 |
| `DUPLICATE_EMAIL` | 409 | 邮箱已存在 |
| `CIRCUIT_BREAKER_OPEN` | 503 | 熔断器开启 |
| `RATE_LIMIT_EXCEEDED` | 429 | 限流触发 |
| `UNKNOWN_ERROR` | 500 | 未知错误 |

## 12. 错误响应格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "priority 必须为 low/medium/high",
    "details": [
      { "field": "priority", "issue": "must be one of: low, medium, high" }
    ]
  }
}
```
