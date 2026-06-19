# 多智能体协同框架 - 安全设计 (SECURITY.md)

## 1. 认证体系

### 1.1 双认证机制

| 用户类型 | 认证方式 | 说明 |
|----------|----------|------|
| 用户 | JWT access_token | 登录后获得，有效期 1h；通过 Authorization: Bearer 传递 |
| 用户（续期） | JWT refresh_token | HttpOnly Cookie，有效期 7d，JS 不可读，仅用于 /auth/refresh |
| 服务间 | API Key | 通过 X-API-Key Header 传递 |

### 1.2 JWT 配置

```python
ACCESS_TOKEN_EXPIRE_SEC  = 1 * 60 * 60       # 1 小时
REFRESH_TOKEN_EXPIRE_SEC = 7 * 24 * 60 * 60  # 7 天
ALGORITHM = "HS256"
```

### 1.3 refresh_token 存储与传递

- 登录时后端通过 `Set-Cookie: refresh_token=...; HttpOnly; SameSite=Strict; Path=/api/v1/auth/refresh` 写入浏览器
- 前端 JS 不可读取（HttpOnly），无需处理
- 刷新时浏览器自动携带该 Cookie，后端从 Cookie 读取
- 退出登录时后端清除该 Cookie

---

## 2. 限流策略

### 2.1 Token Bucket 算法

| 路径 | 请求/分钟 | 说明 |
|------|-----------|------|
| `/api/v1/auth/*` | 10 | 认证接口严格限流，防暴力破解 |
| `/api/v1/tasks` | 100 | 任务创建 |
| `/api/v1/tasks/{id}` | 300 | 任务查询 |
| `/api/v1/skills/*` | 50 | Skill 操作 |
| `/api/v1/dashboard` | 60 | 仪表盘聚合查询 |

### 2.2 按用户维度限流

- 每个 API Key 独立 Bucket（基于 Redis 计数器）
- 超限返回 `429 Too Many Requests`，Header 中附带 `Retry-After`

---

## 3. 输入校验

### 3.1 Pydantic Schema 校验

```python
class TaskCreateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    priority: str = Field(..., pattern="^(low|medium|high)$")
    expected_models: List[str] = Field(default_factory=list)

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @validator('password')
    def password_strength(cls, v):
        if not re.search(r'[A-Z]', v): raise ValueError('需含大写字母')
        if not re.search(r'[a-z]', v): raise ValueError('需含小写字母')
        if not re.search(r'\d', v):    raise ValueError('需含数字')
        return v
```

### 3.2 Prompt 注入防护

- 检测常见注入关键词（`system:`、`ignore previous`、`<|endoftext|>` 等）
- 用户输入与系统 Prompt 严格隔离，使用分隔符包裹：`<user_input>...</user_input>`
- 输出内容校验（防止 LLM 输出含 XSS payload）

---

## 4. Skill 沙箱

### 4.1 执行约束

| 约束 | 限制 | 说明 |
|------|------|------|
| 时间 | 30s | 单个 Skill 执行超时 |
| 内存 | 256MB | 内存上限 |
| 网络 | 白名单 | 仅允许访问白名单域名 |
| 文件 | 只读/指定目录 | 禁止访问系统文件 |

### 4.2 依赖白名单

```yaml
allowed_dependencies:
  - requests
  - pydantic
  - numpy
  - pandas
```

---

## 5. CORS 配置

```python
CORS_CONFIG = {
    "origins": ["http://localhost:3000"],   # 开发环境；生产由环境变量 CORS_ORIGINS 注入
    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
    "allow_credentials": True,             # 必须开启，否则浏览器不会携带 Cookie（refresh_token）
    "allow_headers": ["Authorization", "X-API-Key", "X-Request-Id", "Content-Type"],
}
```

---

## 6. 文件上传安全

### 6.1 Skill 安装包上传

- 限制文件类型：仅 `.tar.gz`、`.whl`、`.zip`
- 限制文件大小：最大 50MB
- 解压后静态扫描：检查导入的模块是否在白名单内
- 安装到隔离目录：`/opt/agentforge/skills/`

---

## 7. Secrets 管理

### 7.1 LLM API Key 存储

- 不在数据库中明文存储
- 通过环境变量注入，生产环境使用密钥管理服务（如 HashiCorp Vault）
- 支持多 Key 轮换，自动切换

### 7.2 密码存储

- 使用 bcrypt 哈希存储，盐值 12 轮
- 不在日志中记录任何密码字段

---

## 8. HTTPS 与传输安全

- 生产环境强制 HTTPS（Nginx 配置 HTTP → HTTPS 301 重定向）
- TLS 1.2+，HSTS Header（`max-age=31536000; includeSubDomains`）
- 数据库连接使用 SSL（`postgresql+asyncpg://...?ssl=require`）

---

## 9. XSS 防护

- Vue 自动转义插值内容
- Markdown 渲染使用 `dompurify` 过滤（`markdown-it + dompurify`）
- CSP Header（Nginx 配置）：`default-src 'self'; script-src 'self'`

---

## 10. CSRF 防护

- `refresh_token` Cookie 设置 `SameSite=Strict`，阻止跨站请求自动携带
- `access_token` 通过 Authorization Header 传递，CSRF 无法伪造 Header
- 生产环境 CORS 严格配置，仅允许指定 Origin

---

## 11. 审计日志

### 11.1 全链路 Trace ID

- 每个请求生成唯一 `trace_id`（UUID），贯穿所有 Agent/Skill 调用
- 可通过 `trace_id` 查询完整调用链

### 11.2 日志格式

```json
{
  "timestamp": "2026-06-17T10:00:00Z",
  "level": "INFO",
  "trace_id": "trace-001",
  "user_id": "user-001",
  "action": "task_create",
  "resource": "task-001",
  "ip": "192.168.1.1",
  "status": "success"
}
```

---

## 12. 数据脱敏

### 12.1 自动脱敏规则

| 数据类型 | 脱敏方式 | 示例 |
|----------|----------|------|
| 邮箱 | 保留域名 | `u***@example.com` |
| 手机号 | 保留后 4 位 | `138****1234` |
| 身份证 | 保留后 4 位 | `***1234` |
| 密码 | 不记录 | - |
| LLM API Key | 不记录 | - |

### 12.2 导出时脱敏

- 训练数据导出前自动应用脱敏规则
- 可配置脱敏级别（Level 0/1/2），详见 DATA-EXPORT.md
