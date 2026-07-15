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

## Project / Mount / Artifact API

Project 是 AgentForge 面向终端全栈开发工程师的上下文容器。所有接口均按当前登录用户隔离，访问其他用户的 Project、Mount、Artifact 返回 404。

### 创建项目

```http
POST /api/v1/projects
Authorization: Bearer <token>

{
  "name": "我的电商后端",
  "description": "FastAPI + Vue 3 电商项目",
  "tech_tags": ["FastAPI", "Vue 3", "PostgreSQL"]
}
```

**响应 201**:
```json
{
  "id": "project-001",
  "user_id": "user-001",
  "name": "我的电商后端",
  "display_name": "我的电商后端",
  "description": "FastAPI + Vue 3 电商项目",
  "tech_tags": ["FastAPI", "Vue 3", "PostgreSQL"],
  "status": "active",
  "created_at": "2026-07-08T10:00:00Z",
  "updated_at": "2026-07-08T10:00:00Z"
}
```

### 项目 CRUD

```http
GET    /api/v1/projects
GET    /api/v1/projects/{project_id}
PATCH  /api/v1/projects/{project_id}
DELETE /api/v1/projects/{project_id}
```

`DELETE` 为软删除，将 `status` 置为 `archived`。

### 项目会话

```http
POST /api/v1/projects/{project_id}/sessions
GET  /api/v1/projects/{project_id}/sessions
```

创建请求：
```json
{
  "title": "设计订单退款流程",
  "intent_type": "new_feature"
}
```

响应字段包含 `project_id`、`intent_type`、`current_pipeline_run_id`。旧入口 `POST /api/v1/sessions` 仍保留，但会自动创建或复用当前用户的“默认项目”。

`POST /api/v1/sessions/{session_id}/chat` 首次发送消息时会根据请求中的 `intent` 和 `stage_overrides` 创建 `PipelineRun`；响应在原有 `message_id`、`task_id` 基础上增加 `pipeline_run_id`，前端据此拉取阶段运行态。

`context_files[type=file]` 可携带 `mount_id`。当 `mount_id` 指向当前项目的 connected local mount 时，后端会在任务执行前读取授权 root 内的真实文件内容，并注入 SkillExecutionEngine；未携带 `mount_id` 的 file 仍只是用户提供的路径线索。

### ProjectMount

```http
GET    /api/v1/projects/{project_id}/mounts
POST   /api/v1/projects/{project_id}/mounts
PATCH  /api/v1/projects/{project_id}/mounts/{mount_id}
DELETE /api/v1/projects/{project_id}/mounts/{mount_id}
```

创建请求：
```json
{
  "mount_type": "local",
  "display_name": "shop-api",
  "locator": "/Users/me/work/shop-api",
  "role": "primary",
  "status": "pending",
  "metadata": {}
}
```

`mount_type` 取值：`local`、`github`、`upload`。TASK-018 后 connected local mount 可通过 Bridge 读取授权 root 内的 UTF-8 文本文件。

### Upload Mount

Upload Mount 是无法连接本地目录或 GitHub 时的只读上下文兜底。它只读取用户主动上传的 manifest 文件，不访问用户本地路径，也不允许作为写回目标。

```http
POST /api/v1/projects/{project_id}/mounts/upload
Content-Type: multipart/form-data
```

表单字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `display_name` | string | Mount 展示名 |
| `role` | string | `primary` / `reference` / `docs`，默认 `docs` |
| `files` | file[] | 一个或多个 UTF-8 文本文件 |
| `paths` | string[] | 可选，相对路径；不传时使用文件名 |

响应为 connected `ProjectMount`：

```json
{
  "mount_type": "upload",
  "locator": "upload://<upload_id>",
  "status": "connected",
  "metadata": {
    "upload_id": "<upload_id>",
    "file_count": 1,
    "total_bytes": 128,
    "manifest": [
      {
        "path": "docs/requirements.md",
        "size": 128,
        "mime_type": "text/markdown",
        "sha256": "...",
        "storage_path": "docs/requirements.md",
        "uploaded_at": "2026-07-08T10:00:00Z"
      }
    ]
  }
}
```

规则：

- 上传路径必须是相对路径，拒绝绝对路径、`..`、反斜杠、Windows 盘符、控制字符和重复路径。
- 文件必须是 UTF-8 文本，扩展名、单文件大小、总大小和文件数量由 `UPLOAD_MOUNT_*` 配置控制。
- `GET /mounts/{mount_id}/files` 与 `POST /files/read` 支持 connected upload Mount，但只返回 manifest 范围内文件。
- 删除 Upload Mount 时清理对应服务端文件集合。
- 审计事件包括 `upload_mount.file.uploaded`、`upload_mount.file.read`、`upload_mount.deleted`、`upload_mount.failed`，details 不记录文件正文。

### GitHub OAuth Mount

GitHub Mount 必须由当前登录用户在指定 Project 下显式授权创建。OAuth token 只保存在服务端加密凭证表，前端响应、`ProjectMount.metadata`、审计日志和 Delivery report 均不得包含明文 token。

```http
POST /api/v1/projects/{project_id}/mounts/github/oauth/start
Authorization: Bearer <token>

{
  "repo_full_name": "acme/shop-api",
  "role": "primary",
  "redirect_uri": "http://localhost:3000/api/v1/projects/project-001/mounts/github/oauth/callback"
}
```

**响应 201**:
```json
{
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...&state=...",
  "state": "opaque-csrf-state",
  "expires_at": "2026-07-08T10:10:00Z"
}
```

说明：

- `repo_full_name` 必须是 `owner/name` 格式，前端可把 `https://github.com/owner/name` 规整后传入。
- `redirect_uri` 可选；前端推荐传入当前 Project 专属 callback 地址，避免服务端全局配置推断项目。客户端传入的 URI 必须是 `http(s)://host/api/v1/projects/{project_id}/mounts/github/oauth/callback`，否则返回 400。
- `state` 绑定当前 `user_id`、`project_id`、provider、repo 和 10 分钟过期时间。
- 如果 `GITHUB_OAUTH_CLIENT_ID` 或 redirect URI 未配置，返回 503，并写入 `github_mount.oauth.failed`。

授权回调：

```http
GET /api/v1/projects/{project_id}/mounts/github/oauth/callback?code=...&state=...
```

**响应 201**:
```json
{
  "id": "mount-001",
  "project_id": "project-001",
  "mount_type": "github",
  "display_name": "shop-api",
  "locator": "github://acme/shop-api",
  "role": "primary",
  "status": "connected",
  "metadata": {
    "repo_owner": "acme",
    "repo_name": "shop-api",
    "repo_full_name": "acme/shop-api",
    "default_branch": "main",
    "html_url": "https://github.com/acme/shop-api",
    "permission_summary": ["repo"],
    "credential_id": "credential-001"
  },
  "created_at": "2026-07-08T10:00:00Z",
  "updated_at": "2026-07-08T10:00:00Z"
}
```

说明：OAuth callback 是 GitHub 浏览器重定向路径，通常不会携带 `Authorization` header。后端通过一次性 `state` 找回发起授权的 `user_id` 和 `project_id`，并在成功后消费 state。

删除 GitHub Mount 时，`DELETE /api/v1/projects/{project_id}/mounts/{mount_id}` 会标记关联 `OAuthCredential.revoked_at`，并写入 `github_mount.revoked` 审计。GitHub OAuth 审计事件包括：`github_mount.oauth.started`、`github_mount.oauth.succeeded`、`github_mount.oauth.failed`、`github_mount.revoked`。

### Agent Bridge

```http
GET  /api/v1/projects/{project_id}/bridge/status
GET  /api/v1/projects/{project_id}/mounts/{mount_id}/files?path=src
POST /api/v1/projects/{project_id}/mounts/{mount_id}/files/read
```

Bridge 状态响应：
```json
{
  "project_id": "project-001",
  "connected_mounts": 1,
  "mounts": [
    {
      "mount_id": "mount-001",
      "mount_type": "local",
      "display_name": "shop-api",
      "role": "primary",
      "status": "connected",
      "root_path": "/Users/me/work/shop-api"
    }
  ]
}
```

目录列表响应：
```json
{
  "mount_id": "mount-001",
  "project_id": "project-001",
  "path": "src",
  "entries": [
    {
      "name": "main.py",
      "relative_path": "src/main.py",
      "kind": "file",
      "size": 1280,
      "modified_at": "2026-07-08T13:30:00Z"
    }
  ]
}
```

文件读取请求：
```json
{ "path": "src/main.py" }
```

文件读取响应：
```json
{
  "mount_id": "mount-001",
  "project_id": "project-001",
  "path": "src/main.py",
  "content": "print('hello')\n",
  "size": 15,
  "truncated": false
}
```

安全规则：

- `mount_id` 必须属于当前登录用户的当前 Project。
- 只支持 connected local mount；disconnected/pending/error 返回 409。
- 请求 path 必须是相对路径，绝对路径和 `..` 穿越返回 400。
- `.env`、`.env.*`、私钥、`.pem`、`.key`、`.p12`、`.pfx` 等敏感文件返回 403。
- 文件读取仅支持 UTF-8 文本；二进制或非 UTF-8 返回 415。
- 列表接口过滤 `.git`、`node_modules`、`.venv`、`dist`、`build` 等高噪声目录。

### Artifact

```http
GET    /api/v1/projects/{project_id}/artifacts
POST   /api/v1/projects/{project_id}/artifacts
GET    /api/v1/artifacts/{artifact_id}
PATCH  /api/v1/artifacts/{artifact_id}
DELETE /api/v1/artifacts/{artifact_id}
```

创建请求：
```json
{
  "session_id": "session-001",
  "artifact_type": "prd",
  "name": "PRODUCT-REQUIREMENTS.md",
  "content": "# 退款流程优化",
  "file_type": "markdown",
  "metadata": { "stage": "requirements" }
}
```

`artifact_type` 取值：`prd`、`architecture`、`api_spec`、`code`、`test`、`report`、`diff`。

Artifact 响应包含 Delivery 状态：

```json
{
  "metadata": {
    "runtime": {
      "agent_profile": {
        "id": "system-default",
        "name": "CodeSoul",
        "source": "system_default"
      },
      "model_route": {
        "route_key": "default",
        "name": "Legacy Settings",
        "source": "legacy_settings"
      },
      "model_name": "openai/deepseek-v4-pro",
      "skill_policy_key": "default"
    }
  },
  "delivery_status": "pending",
  "delivery_target_path": null,
  "delivered_at": null,
  "delivery_report": null
}
```

MVP 阶段 Artifact 正文保存在数据库 `content` 字段。TASK-016 已落地 Artifact Viewer、Chat ArtifactCard、Project 最近产物列表和作为 `context_files[type=artifact]` 复用；TASK-044 后，StageRuntime 生成的 Artifact 会在 `metadata.runtime` 中返回非敏感运行来源，包含 AgentProfile、ModelRoute、model name 和 SkillPolicy key。对象存储和多人共享权限不在本阶段范围内。

### Artifact Delivery

```http
POST /api/v1/artifacts/{artifact_id}/delivery/preview
POST /api/v1/artifacts/{artifact_id}/delivery/apply
POST /api/v1/artifacts/{artifact_id}/delivery/github/preview
POST /api/v1/artifacts/{artifact_id}/delivery/github/apply
POST /api/v1/artifacts/{artifact_id}/delivery/zip/preview
POST /api/v1/artifacts/{artifact_id}/delivery/zip/apply
GET  /api/v1/artifacts/{artifact_id}/delivery/zip/download
GET  /api/v1/artifacts/{artifact_id}/delivery/report
```

预览请求：

```json
{
  "mount_id": "mount-001",
  "target_path": "src/main.py"
}
```

预览响应：

```json
{
  "artifact_id": "artifact-001",
  "project_id": "project-001",
  "mount_id": "mount-001",
  "target_path": "src/main.py",
  "status": "previewed",
  "has_changes": true,
  "unified_diff": "--- a/src/main.py\\n+++ b/src/main.py\\n@@ -1 +1 @@\\n-old\\n+new\\n",
  "report": {
    "mount_id": "mount-001",
    "target_path": "src/main.py",
    "bytes_to_write": 128,
    "target_fingerprint": {
      "exists": true,
      "size": 36,
      "mtime_ns": 1720425600000000000,
      "sha256": "..."
    }
  }
}
```

写回请求必须显式确认：

```json
{
  "mount_id": "mount-001",
  "target_path": "src/main.py",
  "confirm_write": true,
  "expected_target_hash": "<preview.report.target_fingerprint.sha256>"
}
```

规则：

- `preview` 只生成 unified diff，不写入文件。
- `apply` 在 `confirm_write` 非 `true` 时返回 409。
- `apply` 可传 `expected_target_hash`。如果目标文件当前 sha256 与预览时不一致，返回 409，Artifact 置为 `delivery_status=failed`，并保存失败报告。
- `mount_id` 必须属于 Artifact 所在 Project，并且是 connected local Mount。
- `target_path` 必须位于授权 root 内；绝对路径、`..` 穿越、`.env` 和私钥类敏感文件会被拒绝。
- 写回前若目标文件存在，会在同目录生成 `.agentforge.bak` 备份路径并写入 `delivery_report`。
- 写回成功、未确认拒绝、目标冲突、Bridge 写入失败都会写入 `AuditLog.resource=artifact_delivery`。审计 details 不记录 Artifact 正文。
- Bridge 写入失败时，Artifact 置为 `delivery_status=failed`，`delivery_report` 包含 `phase`、`error_code`、`error_message`、`recovery_hint`。
- `GET /delivery/report` 在 Artifact 已交付后返回 `text/markdown`，用于导出 Delivery report；未交付返回 409。

GitHub PR preview 请求：

```json
{
  "mount_id": "mount-github",
  "target_path": "src/main.py",
  "base_branch": "main",
  "target_branch": "agentforge/artifact-001",
  "pr_title": "Deliver main.py"
}
```

GitHub PR preview 响应：

```json
{
  "artifact_id": "artifact-001",
  "project_id": "project-001",
  "mount_id": "mount-github",
  "target_path": "src/main.py",
  "status": "previewed",
  "has_changes": true,
  "unified_diff": "--- a/src/main.py\\n+++ b/src/main.py\\n@@ -1 +1 @@\\n-old\\n+new\\n",
  "report": {
    "delivery_channel": "github_pr",
    "repo_full_name": "acme/shop-api",
    "target_path": "src/main.py",
    "base_branch": "main",
    "target_branch": "agentforge/artifact-001",
    "base_sha": "base-sha",
    "target_file_sha": "file-sha",
    "pr_title": "Deliver main.py"
  }
}
```

GitHub PR apply 请求必须显式确认，并带回 preview 阶段的 base sha：

```json
{
  "mount_id": "mount-github",
  "target_path": "src/main.py",
  "base_branch": "main",
  "target_branch": "agentforge/artifact-001",
  "pr_title": "Deliver main.py",
  "commit_message": "Deliver main.py",
  "confirm_write": true,
  "expected_base_sha": "base-sha"
}
```

GitHub PR apply 成功后，Artifact `delivery_report` 包含：

```json
{
  "delivery_channel": "github_pr",
  "repo_full_name": "acme/shop-api",
  "delivery_target_path": "github://acme/shop-api/src/main.py",
  "base_branch": "main",
  "target_branch": "agentforge/artifact-001",
  "base_sha": "base-sha",
  "commit_sha": "commit-sha",
  "commit_url": "https://github.com/acme/shop-api/commit/commit-sha",
  "pr_url": "https://github.com/acme/shop-api/pull/42",
  "pr_number": 42,
  "recovery_hint": "Review the PR before merge..."
}
```

规则：

- GitHub PR Delivery 只接受 connected GitHub Mount，且 Mount 必须关联当前用户未撤销的 `OAuthCredential`。
- `preview` 只读取 GitHub base ref 和目标文件，不创建 branch、commit 或 PR。
- `apply` 在 `confirm_write` 非 `true` 时返回 409。
- `apply` 的 `expected_base_sha` 与当前 base branch sha 不一致时返回 409，Artifact 标记为 `failed`，`delivery_report.error_code=github_base_changed`。
- 成功 apply 依次创建 branch、commit 和 PR；阶段事件写入 `AuditLog.resource=artifact_delivery`。
- 审计事件包括 `delivery.github.preview.succeeded`、`delivery.github.apply.denied`、`delivery.github.apply.branch_created`、`delivery.github.apply.commit_created`、`delivery.github.apply.pr_created`、`delivery.github.apply.conflict`、`delivery.github.apply.failed`、`delivery.github.apply.succeeded`。
- API 响应、Delivery report 和 AuditLog details 不包含明文 GitHub token 或 Artifact 正文。

zip Delivery preview 请求：

```json
{
  "target_path": "src/main.py",
  "files": [
    {
      "path": "src/main.py",
      "content": "print('hello')\n"
    }
  ]
}
```

`target_path` 和 `files` 都可选。未传 `files` 时，后端默认把当前 Artifact 内容打包到 `target_path`；未传 `target_path` 时使用 Artifact 名称或 `artifact-<id>.txt`。

zip Delivery preview 响应：

```json
{
  "artifact_id": "artifact-001",
  "project_id": "project-001",
  "mount_id": "zip",
  "target_path": "src/main.py",
  "status": "previewed",
  "has_changes": true,
  "unified_diff": "",
  "report": {
    "delivery_channel": "zip",
    "package_name": "artifact-001-delivery.zip",
    "file_count": 1,
    "total_bytes": 15,
    "package_sha256": "zip-sha256",
    "files": [
      {
        "path": "src/main.py",
        "size": 15,
        "sha256": "file-sha256"
      }
    ]
  }
}
```

zip Delivery apply 请求必须显式确认：

```json
{
  "target_path": "src/main.py",
  "confirm_write": true
}
```

apply 成功后，Artifact `delivery_report` 包含：

```json
{
  "delivery_channel": "zip",
  "package_id": "pkg-001",
  "package_name": "artifact-001-delivery.zip",
  "download_url": "/api/v1/artifacts/artifact-001/delivery/zip/download",
  "file_count": 1,
  "total_bytes": 15,
  "package_sha256": "zip-sha256",
  "expires_at": "2026-07-09T10:00:00Z",
  "recovery_hint": "Download the zip package before it expires."
}
```

规则：

- zip Delivery 不写入用户本地目录，不调用远程仓库 API。
- 包内路径必须是相对路径，拒绝空路径、绝对路径、`..`、反斜杠、Windows 盘符、控制字符和重复路径。
- zip 包固定包含 `manifest.json`、`delivery-report.md` 和 `files/<relative path>`。
- `preview` 只计算 deterministic zip sha256 和包结构，不写服务端下载文件。
- `apply` 在 `confirm_write` 非 `true` 时返回 409。
- `GET /delivery/zip/download` 必须通过 Artifact 所属 Project 权限校验；其他用户访问返回 404。
- API 响应、Delivery report 和 AuditLog details 不暴露服务器临时路径，也不记录 Artifact 正文。
- 审计事件包括 `delivery.zip.preview.succeeded`、`delivery.zip.preview.failed`、`delivery.zip.apply.denied`、`delivery.zip.apply.succeeded`、`delivery.zip.apply.failed`。

### 会话消息中的 Artifact

```http
GET /api/v1/sessions/{session_id}/messages
```

每条消息响应增加 `artifacts` 数组；当 Artifact 的 `source_message_id` 指向该 assistant 消息时，前端会在聊天气泡中展示 ArtifactCard。

---

## Pipeline Catalog API

Pipeline Catalog 是 intent -> StageDefinition 的后端事实源。前端用于渲染需求类型阶段、默认快捷动作和输入 placeholder；StageRuntime 和 PipelineService 用同一份定义创建阶段状态并补充运行上下文。

```http
GET /api/v1/pipeline/catalog
GET /api/v1/pipeline/catalog/{intent_type}
Authorization: Bearer <token>
```

`intent_type` 支持 `new_feature`、`iteration`、`ui_adjust`、`bug_fix`。未知 intent 在单项查询中返回 404；运行时创建 PipelineRun 时未知 intent 仍按兼容逻辑回退到 `iteration`。

列表响应：

```json
{
  "items": [
    {
      "intent_type": "iteration",
      "label": "迭代优化",
      "description": "改现有逻辑、范围局部、不新增核心实体时使用。",
      "placeholder": "描述你的迭代需求，例如：优化订单列表加载性能...",
      "stages": [
        {
          "stage_id": "diff",
          "stage_name": "需求 Diff",
          "description": "描述本次变化和旧行为差异。",
          "order_index": 0,
          "required": true,
          "confirmation_required": true,
          "confirmation_policy": {
            "required": true,
            "type": "stage_output",
            "gate": "diff_review"
          },
          "required_input_artifact_types": [],
          "output_artifact_types": ["diff"],
          "success_criteria": [
            "描述旧行为、新行为和不变范围。",
            "给出验收差异。"
          ],
          "default_agent_selector": "planner",
          "model_route_key": "default",
          "skill_policy_key": "default",
          "can_skip": false,
          "can_restore": false
        }
      ],
      "default_actions": [
        {
          "id": "analyze_diff",
          "label": "分析需求变更",
          "prompt": "帮我分析这次需求变更的具体内容和影响范围。",
          "highlighted": true
        }
      ]
    }
  ]
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `stages[].required` | 是否为必需阶段；只有 `false` 阶段允许 skip/restore。 |
| `stages[].confirmation_policy` | 当前阶段确认策略；StageState 初始化时由 GovernancePolicy 生成确认类型、原因和影响范围。 |
| `stages[].required_input_artifact_types` | 阶段需要消费的前序 Artifact 类型；运行时会据此筛选上下文并报告缺失类型。 |
| `stages[].output_artifact_types` | 阶段预期产物类型，用于 Artifact 归档和后续展示。 |
| `stages[].output_contract_key` | 可选结构化输出合同；`task_split` 当前为 `task_graph_v1`。 |
| `stages[].success_criteria` | 阶段完成标准；StageRuntime 会把它作为可信阶段指令传给 SkillExecutionEngine。 |
| `stages[].default_agent_selector` | AgentResolver 的默认选择线索，StageRuntime 会据此选择 AgentProfile。 |
| `stages[].model_route_key` | StageRuntime 实际解析到的 ModelRoute key。 |
| `stages[].skill_policy_key` | Stage 级 Skill 策略 key；当前已接入 Skill 调用前权限校验和高风险 Governance 决策，精细化白名单仍可后续增强。 |

### StageExecutionContext 运行时契约

TASK-047 后，StageRuntime 会从 Catalog 构建 `advanced_context.stage_execution`。该对象包含当前 Project、Session、PipelineRun、Stage 的标识，阶段目标、必需输入类型、预期输出类型、结构化输出合同、完成标准、缺失输入类型和有界前序 Artifact。

上下文只查询当前 `project_id + pipeline_run_id`，只接受真实 `stage_state_id` 对应的前序阶段，并按“阶段状态 + Artifact 类型”保留最新版本后应用预算：最多 6 项、单项最多 4000 字符、正文总计最多 12000 字符。总预算在入选项之间公平分配，避免首项耗尽上下文。

阶段定义和完成标准进入 system prompt 的可信指令区；Artifact 正文只进入 user-level reference，并以 `trust_level="untrusted"` 标记和转义边界字符。`missing_input_artifact_types` 当前只提示，不阻断执行；硬门禁由 TASK-051 VerificationGate 实现。

---

## PipelineRun / StageState API

PipelineRun 是一次 Session 内按需求类型生成的阶段计划；PipelineStageState 是每个阶段的运行时状态。所有接口按当前登录用户隔离，访问其他用户的 run 返回 404。

### 创建会话 PipelineRun

```http
POST /api/v1/sessions/{session_id}/pipeline-runs
Authorization: Bearer <token>

{
  "intent_type": "iteration",
  "stage_overrides": {
    "impact": false,
    "frontend_dev": false
  }
}
```

**响应 201**:
```json
{
  "id": "run-001",
  "project_id": "project-001",
  "session_id": "session-001",
  "intent_type": "iteration",
  "status": "planned",
  "current_stage_id": "diff",
  "created_at": "2026-07-08T10:00:00Z",
  "updated_at": "2026-07-08T10:00:00Z",
  "stages": [
    {
      "id": "stage-001",
      "pipeline_run_id": "run-001",
      "stage_id": "diff",
      "stage_name": "需求 Diff",
      "order_index": 0,
      "required": true,
      "status": "pending",
      "skip_reason": null,
      "confirmation_required": true,
      "confirmation_type": "diff_review",
      "confirmation_reason": "迭代差异会决定实际改动范围，继续前需要用户确认。",
      "confirmation_impact_scope": [
        {
          "type": "pipeline_stage",
          "id": "diff",
          "label": "需求 Diff"
        }
      ],
      "confirmation_audit_payload": {
        "decision": "require_confirmation",
        "risk_level": "medium",
        "confirmation_type": "diff_review"
      },
      "confirmation_action": null,
      "confirmation_feedback": null,
      "confirmation_resolved_at": null,
      "agent_profile_id": null,
      "agent_profile_name": null,
      "agent_profile_source": null,
      "model_route_key": null,
      "model_route_name": null,
      "model_name": null,
      "model_route_source": null,
      "started_at": null,
      "completed_at": null,
      "created_at": "2026-07-08T10:00:00Z",
      "updated_at": "2026-07-08T10:00:00Z"
    }
  ]
}
```

`intent_type` 支持 `new_feature`、`iteration`、`ui_adjust`、`bug_fix`。`stage_overrides` 仅允许跳过可选阶段，必需阶段无法跳过。

### 查询 PipelineRun

```http
GET /api/v1/pipeline-runs/{run_id}
Authorization: Bearer <token>
```

响应结构同创建接口。

### 查询 TaskGraph

TASK-049 后，`task_split` 阶段的 `task_graph_v1` 输出会在同一事务内生成 TaskGraph 和可读 Artifact。TaskGraph 是后续 WorkspaceExecutor 与 VerificationGate 的结构化事实源。

```http
GET /api/v1/pipeline-runs/{run_id}/task-graph
Authorization: Bearer <token>
```

**响应 200**:

```json
{
  "id": "graph-001",
  "project_id": "project-001",
  "pipeline_run_id": "run-001",
  "source_stage_state_id": "stage-task-split",
  "source_artifact_id": "artifact-task-split",
  "schema_version": 1,
  "status": "ready",
  "summary": "实现用户通知设置",
  "created_at": "2026-07-15T10:00:00Z",
  "updated_at": "2026-07-15T10:00:00Z",
  "nodes": [
    {
      "id": "node-backend",
      "key": "backend-api",
      "title": "新增通知设置 API",
      "description": "实现模型、服务和路由",
      "order_index": 0,
      "status": "pending",
      "depends_on": [],
      "acceptance_criteria": ["API 权限和错误响应符合契约"],
      "target_files": ["src/api/routes/notifications.py"],
      "verification_commands": ["pytest -q tests/api/test_notifications.py"],
      "created_at": "2026-07-15T10:00:00Z",
      "updated_at": "2026-07-15T10:00:00Z"
    }
  ]
}
```

接口先按当前用户校验 PipelineRun 所有权，再加载图。其他用户、Run 不存在或图尚未生成均返回 404，不暴露资源是否属于其他账号。节点按 `order_index` 返回，`depends_on` 使用同图 node key。

### WorkspaceExecutor Preview / Apply

TASK-050 后，TaskNode 可在用户授权的 connected local primary Mount 内生成持久化多文件变更。Preview 不写文件；Apply 必须经过 `workspace_write` GovernancePolicy 确认、WorkspaceChangeSet 行锁和全部文件基线校验。

```http
POST /api/v1/task-graphs/{graph_id}/nodes/{node_key}/workspace/preview
GET  /api/v1/workspace-change-sets/{change_set_id}
POST /api/v1/workspace-change-sets/{change_set_id}/apply
Authorization: Bearer <token>
```

Preview 请求：

```json
{
  "mount_id": "mount-001",
  "source_artifact_id": "artifact-code-001",
  "files": [
    {
      "path": "src/api/routes/notifications.py",
      "content": "..."
    }
  ]
}
```

**Preview 响应 201 / 查询响应 200**：

```json
{
  "id": "change-set-001",
  "project_id": "project-001",
  "task_graph_id": "graph-001",
  "task_node_id": "node-backend",
  "mount_id": "mount-001",
  "status": "previewed",
  "has_changes": true,
  "apply_report": null,
  "patches": [
    {
      "target_path": "src/api/routes/notifications.py",
      "operation": "upsert",
      "status": "previewed",
      "has_changes": true,
      "unified_diff": "--- a/src/api/routes/notifications.py\n+++ b/src/api/routes/notifications.py\n...",
      "base_fingerprint": {
        "exists": true,
        "size": 128,
        "sha256": "..."
      }
    }
  ]
}
```

响应不返回 `proposed_content`。Preview 最多 50 个文件，单文件最多 200000 bytes，总候选正文最多 2000000 bytes；路径必须同时属于 TaskNode.target_files 并通过 Bridge 敏感路径和授权根校验。

Apply 请求：

```json
{"confirm_write": true}
```

成功返回 200 和 `status=applied` 的同一 ChangeSet；重复 Apply 幂等返回已有 ApplyReport，不再次写文件。未确认、基线冲突、applying/failed 状态返回 409；failed 版本必须重新 Preview。冲突、回滚和审计只记录路径、指纹、字节数与错误元数据，不记录源码正文。

### 阶段状态操作

```http
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/skip
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/restore
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/start
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/complete
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/confirm
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/fail
```

- `skip` 仅支持 `required=false` 且未 completed/running 的阶段，成功后 `status=skipped`。
- `restore` 将 skipped 的可选阶段恢复为 `pending`。
- `start` 仅将 `pending` 阶段置为 `running`，并设置 run 的 `current_stage_id`；`waiting_confirmation` 不允许通过 `start` 绕过确认。
- `complete` 将非确认阶段置为 `completed` 并推进到下一个未 completed/skipped 阶段；若阶段 `confirmation_required=true`，则进入 `waiting_confirmation`，等待 `confirm`。
- `confirm` 是等待态的唯一出口，支持 `approve`、`revise`、`cancel`。
- `fail` 将阶段与 run 置为 `failed`。

确认请求：

```json
{
  "action": "revise",
  "feedback": "补充异常场景和验收标准"
}
```

`action=approve` 会把当前阶段置为 `completed` 并推进到下一阶段；`action=revise` 会把当前阶段回到 `pending`，`feedback` 注入下一次同阶段执行上下文；`action=cancel` 会把阶段置为 `failed`、run 置为 `cancelled`。每次确认会写入 `AuditLog.action=pipeline.confirm.{action}`，并在 `details.governance_decision` 中记录确认类型、原因、风险等级和影响范围。

StageRuntime 会在调用现有 `SkillExecutionEngine` 前后自动执行当前阶段的 start/complete；阶段完成后创建 Artifact 并发出 `artifact_created` SSE。`task_split` 会缓冲并严格解析 `task_graph_v1`，再原子创建 Artifact、TaskGraph、TaskNode 和依赖边；成功后聊天只接收可读 Markdown，不展示原始 JSON，非法输出使 Stage/Run failed 且不留下半成品或用户可见的部分输出。需要人工确认的阶段完成后会发出 `confirm_required`，并在确认前停止自动推进。确认原因和影响范围由服务端 `GovernancePolicy` 生成，前端只负责渲染。

StageRuntime 启动阶段时会通过 AgentResolver 选择 AgentProfile，并写入当前 `PipelineStageState.agent_profile_id/name/source`。解析优先级为：用户本次阶段覆盖 → Project 默认 Agent policy → `StageDefinition.default_agent_selector` → 系统默认 Agent。第一版 Project 默认值通过运行时上下文预留，持久化项目策略后续继续扩展。

StageRuntime 启动阶段时也会通过 ModelRouter 选择 ModelRoute，并写入 `PipelineStageState.model_route_key/name/source` 和 `model_name`。解析优先级为：用户本次 `model_route_key` 覆盖 → AgentProfile 默认 route → `StageDefinition.model_route_key` → legacy settings fallback。Credential 明文只用于服务端调用 LLM，不进入 API 响应和 prompt 上下文。

TASK-035 后，StageRuntime 会在调用 SkillExecutionEngine 前按 `StageDefinition.skill_policy_key`、`AgentProfile.allowed_skill_names` 和 `SkillRuntimeSpec.permissions` 过滤 LLM 可见 tools。过滤报告写入 `advanced_context.skill_policy`，其中包含 `policy_key`、输入/允许工具数量、Agent allowlist 和被排除工具的原因。SkillDispatcher 的调用前权限校验仍保留为第二道防线。

TASK-036 后，MCP Server 注册的外部 tool 也会生成 `source_type=mcp` 的 RuntimeSpec；MCP 配置未声明 permissions 时默认按 `credential` 高风险处理，因此不会绕过 Stage 级工具过滤。

TASK-037 后，内置 Skill 注册时也会生成 `source_type=builtin` 的 RuntimeSpec；`external_side_effect` 被归为高风险权限，默认 StageSkillPolicy 会过滤 `http_request`、`update_profile`、`code_executor`。

TASK-038 后，StageRuntime 支持从 `advanced_context.skill_authorization` 读取当前阶段的临时高风险授权：

```json
{
  "skill_authorization": {
    "authorized_skill_names": ["code-executor"],
    "authorized_permissions": ["shell"],
    "source": "user_confirmation"
  }
}
```

该授权只影响本次 StageRuntime 工具过滤，不写入 Agent、Skill 或 StageDefinition。`AgentProfile.allowed_skill_names` 仍优先于临时授权，因此未绑定到当前 Agent 的 Skill 不会被放行。过滤报告会在 `advanced_context.skill_policy` 中回传 `authorized_skill_names`、`authorized_permissions` 和被排除工具原因。

TASK-039 后，Chat 请求体也可以携带同样的 `skill_authorization` 字段；StageRuntime 发现已绑定但被权限策略过滤的高风险 Skill 时会发出 `skill_authorization_required` SSE：

```json
{
  "task_id": "task-id",
  "pipeline_run_id": "run-id",
  "stage_id": "locate",
  "skills": [
    {
      "skill_name": "code-executor",
      "tool_name": "code_executor",
      "permissions": ["shell"]
    }
  ]
}
```

前端确认后会用原消息重试，并把 `skills[].skill_name` 和 `skills[].permissions` 汇总为一次性授权 payload。

TASK-040 后，StageRuntime 会把高风险 Skill 授权事实写入 EvalEvent：

- `skill_authorization_required`：状态为 `blocked`，表示已绑定到当前 Agent 的高风险 Tool 被 StageSkillPolicy 过滤，并已通过 SSE 请求用户确认。
- `skill_authorization_granted`：状态为 `success`，表示一次性 `skill_authorization` 已实际放行某个 Tool。

这两类事件的 metadata 仅包含 `permissions`、`policy_key`、`reason`、`authorized_skill_names`、`authorized_permissions`、`authorized_by`、`source` 等结构化字段，不包含用户消息、源码、文件正文或凭据。

---

## LLM 设置 API

结构化 LLM 配置按当前登录用户隔离，写接口需要 `admin` 权限，读接口需要 `read` 权限。

### 配置快照

```http
GET /api/v1/llm
Authorization: Bearer <token>
```

响应包含旧版全局配置和结构化对象列表：

```json
{
  "api_key_set": true,
  "default_model": "openai/gpt-4o-mini",
  "default_temperature": 0.7,
  "max_tokens": 4096,
  "model_routes": {"vision": "openai/gpt-4o"},
  "providers": [],
  "models": [],
  "credentials": [],
  "routes": []
}
```

### Provider / Model / Credential / Route

```http
POST /api/v1/llm/providers
GET /api/v1/llm/providers
POST /api/v1/llm/models
GET /api/v1/llm/models
POST /api/v1/llm/credentials
GET /api/v1/llm/credentials
POST /api/v1/llm/routes
GET /api/v1/llm/routes
```

Credential 创建请求：

```json
{
  "provider_id": "provider-001",
  "name": "prod-key",
  "secret": "sk-...",
  "active": true
}
```

Credential 响应永不返回明文：

```json
{
  "id": "cred-001",
  "provider_id": "provider-001",
  "provider_key": "openai",
  "name": "prod-key",
  "secret_set": true,
  "masked_secret": "sk-a...1234",
  "active": true
}
```

Route 创建请求：

```json
{
  "route_key": "default",
  "name": "默认路由",
  "provider_id": "provider-001",
  "model_id": "model-001",
  "credential_id": "cred-001",
  "temperature": 0.7,
  "max_tokens": 4096,
  "timeout_seconds": 60,
  "fallback_route_keys": ["safe"],
  "active": true
}
```

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

### 4.3 查询运行时 Agent 候选

```http
GET /api/v1/agents/runtime/candidates?stage_selector=coder
Authorization: Bearer <token>
```

响应：

```json
{
  "items": [
    {
      "id": "agent-001",
      "name": "coder-001",
      "capabilities": ["code_generation", "refactoring"],
      "model": "gpt-4",
      "description": "代码生成专家",
      "avatar_url": null,
      "recommended": true
    }
  ]
}
```

说明：

- 仅返回 `status=active` 的 Agent；禁用 Agent 不会被 StageRuntime 或候选接口选择。
- `recommended=true` 表示 Agent capability 与当前 `stage_selector` 匹配。

### 4.4 更新 Agent

```http
PATCH /api/v1/agents/{agent_id}
Authorization: Bearer <token>   (需要 admin 权限)

{
  "status": "inactive"
}
```

### 4.5 删除 Agent

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
  "version": "1.0.0",
  "confirm_risk": false
}
```

**响应 202**（异步，返回安装任务 ID）:
```json
{
  "install_id": "install-001",
  "skill_name": "my-skill",
  "status": "pending",
  "manifest_hash": "sha256...",
  "permissions": ["network"],
  "risk_level": "medium"
}
```

### 5.1.1 预览第三方 Skill 导入

```http
POST /api/v1/skills/import/preview
Authorization: Bearer <token>   (需要 admin 权限)

{
  "source": "/Users/me/skills/safe-echo",
  "version": "1.0.0"
}
```

支持本地目录、GitHub URL、通用 Git URL 和 PyPI 包名。后端优先读取 `agentforge-skill.yaml`，兼容旧 `skill.md`。

**响应 200**:
```json
{
  "name": "safe-echo",
  "version": "1.0.0",
  "description": "Echo a message.",
  "source": "/Users/me/skills/safe-echo",
  "source_type": "local",
  "manifest_hash": "sha256...",
  "permissions": ["network", "project_context"],
  "risk_level": "medium",
  "requires_confirmation": false,
  "tools": [
    {
      "name": "safe_echo",
      "description": "Echo a message.",
      "parameters": {
        "message": {
          "type": "string"
        }
      }
    }
  ],
  "audit_level": "standard"
}
```

### 5.1.2 安装已预览 Skill

```http
POST /api/v1/skills/import/install
Authorization: Bearer <token>   (需要 admin 权限)

{
  "source": "/Users/me/skills/safe-echo",
  "version": "1.0.0",
  "confirm_risk": false
}
```

高风险权限（`filesystem`、`shell`、`credential`、`external_side_effect`）未确认时响应 `409`：

```json
{
  "detail": {
    "code": "SKILL_PERMISSION_CONFIRMATION_REQUIRED",
    "preview": {
      "name": "shell-skill",
      "permissions": ["shell"],
      "risk_level": "high"
    }
  }
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
      "manifest_hash": "sha256...",
      "permissions": ["network"],
      "runtime_spec": {
        "name": "code-review",
        "tool_defs": []
      },
      "audit_level": "standard",
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
  "evaluation": {
    "total_events": 128,
    "stage_success_rate": 0.92,
    "skill_success_rate": 0.88,
    "delivery_success_rate": 0.95,
    "average_stage_latency_ms": 2450,
    "skill_authorizations": {
      "required": 12,
      "granted": 9,
      "grant_rate": 0.75,
      "by_skill": [
        {
          "skill_name": "code-executor",
          "required": 8,
          "granted": 7,
          "grant_rate": 0.875
        }
      ],
      "by_permission": [
        {
          "permission": "shell",
          "required": 8,
          "granted": 7,
          "grant_rate": 0.875
        }
      ]
    },
    "llm": {
      "total_calls": 6,
      "tokens_used": 4820,
      "cost_usd": 0.034,
      "average_latency_ms": 820,
      "by_model_route": [
        {
          "model_route_key": "default",
          "name": "Default Route",
          "total_calls": 6,
          "tokens_used": 4820,
          "cost_usd": 0.034,
          "average_latency_ms": 820
        }
      ],
      "by_stage": [
        {
          "stage_id": "backend_dev",
          "name": "后端开发",
          "total_calls": 3,
          "tokens_used": 2500,
          "cost_usd": 0.019,
          "average_latency_ms": 760
        }
      ]
    }
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

**说明：** `trend_pct` 为正表示任务费用较昨日增加，为负表示减少。TASK-048 后，`tasks`、`cost` 和 `recent_tasks` 均在 SQL 查询阶段按当前用户的 `Task.user_id` 隔离，无归属 Task 不对普通用户展示；Agent 和 Skill 数量仍表示平台级可用资源。`evaluation` 基于当前用户的 `EvalEvent` 聚合，空数据时返回 0 值，不影响 Dashboard 渲染。TASK-046 后，Dashboard evaluation 同步返回高风险 Skill 授权指标和非流式 LLM 用量指标；`llm.by_model_route` / `llm.by_stage` 只返回成本最高的前 3 项。

---

## 6.1 Evaluation API

```http
GET /api/v1/evaluation/summary?project_id=proj-001&pipeline_run_id=run-001&start_date=2026-07-01T00:00:00Z&end_date=2026-07-10T23:59:59Z
Authorization: Bearer <token>
```

所有过滤参数均可选；传 `project_id` 时只返回当前登录用户有权访问的项目数据。

**响应 200**:
```json
{
  "project_id": "proj-001",
  "pipeline_run_id": "run-001",
  "total_events": 42,
  "period": {
    "start_date": "2026-07-01T00:00:00Z",
    "end_date": "2026-07-10T23:59:59Z"
  },
  "pipelines": {
    "total": 8,
    "succeeded": 7,
    "failed": 1,
    "success_rate": 0.875,
    "average_latency_ms": 2100,
    "cost_usd": 0.0,
    "tokens_used": 0
  },
  "stages": {
    "total": 18,
    "succeeded": 16,
    "failed": 2,
    "success_rate": 0.889,
    "average_latency_ms": 2450,
    "cost_usd": 0.0,
    "tokens_used": 0
  },
  "llm": {
    "total": 6,
    "succeeded": 6,
    "failed": 0,
    "success_rate": 1.0,
    "average_latency_ms": 820,
    "cost_usd": 0.034,
    "tokens_used": 4820
  },
  "llm_by_model_route": [
    {
      "model_route_key": "default",
      "name": "Default Route",
      "total_calls": 6,
      "tokens_used": 4820,
      "cost_usd": 0.034,
      "average_latency_ms": 820
    }
  ],
  "llm_by_stage": [
    {
      "stage_id": "backend_dev",
      "name": "后端开发",
      "total_calls": 3,
      "tokens_used": 2500,
      "cost_usd": 0.019,
      "average_latency_ms": 760
    }
  ],
  "skills": {
    "total": 9,
    "succeeded": 8,
    "failed": 1,
    "success_rate": 0.889,
    "average_latency_ms": 420,
    "cost_usd": 0.0,
    "tokens_used": 0
  },
  "delivery": {
    "total": 4,
    "succeeded": 3,
    "failed": 1,
    "success_rate": 0.75,
    "average_latency_ms": 0,
    "cost_usd": 0.0,
    "tokens_used": 0
  },
  "artifacts": {
    "generated": 6,
    "delivered": 3,
    "failed": 1
  },
  "confirmations": {
    "total": 5,
    "revised": 1,
    "revise_ratio": 0.2
  },
  "skill_authorizations": {
    "required": 2,
    "granted": 1,
    "grant_rate": 0.5,
    "by_skill": [
      {
        "skill_name": "code-executor",
        "required": 1,
        "granted": 1,
        "grant_rate": 1.0
      }
    ],
    "by_permission": [
      {
        "permission": "shell",
        "required": 1,
        "granted": 1,
        "grant_rate": 1.0
      }
    ]
  },
  "agents": [
    {
      "agent_profile_id": "agent-001",
      "name": "Coder",
      "usage_count": 5,
      "failed": 1,
      "failure_rate": 0.2,
      "average_latency_ms": 2300,
      "cost_usd": 0.034,
      "tokens_used": 4820
    }
  ],
  "models": [
    {
      "model_route_key": "default",
      "name": "Default Route",
      "usage_count": 5,
      "failed": 0,
      "failure_rate": 0.0,
      "average_latency_ms": 2300,
      "cost_usd": 0.034,
      "tokens_used": 4820
    }
  ],
  "event_counts": {
    "stage_started": 6,
    "stage_completed": 5,
    "llm_tool_use_completed": 6,
    "delivery_failed": 1
  }
}
```

`skill_authorizations` 只统计 `skill_authorization_required` 和 `skill_authorization_granted` EvalEvent。`by_permission` 从事件 metadata 的 `permissions` 数组聚合；空数据时 `required/granted/grant_rate` 为 0，明细列表为空。

`llm`、`llm_by_model_route` 和 `llm_by_stage` 只统计 `llm_*` EvalEvent。TASK-046 后，StageRuntime 通过规范键 `evaluation_context` 将 Project、PipelineRun、Stage 和非敏感 Stage 名称传给 SkillExecutionEngine；`llm_tool_use_completed` metadata 只包含 `call_type`、轮次、可见工具数量、是否产生 tool call、tool 名称和 Stage 名称，不包含 prompt、用户消息、源码正文或凭据。`stream_complete` 的 token / cost usage 仍未采集，作为后续增强。

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

TASK-048 后，该路由已挂载到主 FastAPI 应用。任务总成本、任务数和 `TaskExecution` 模型费用均通过 `Task.user_id` 按当前认证用户隔离，无归属 Task 不参与统计。Bearer Token 和有效 API Key 均可认证；停用 API Key 返回 401。

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
| `skill_authorization_required` | 当前阶段有已绑定高风险 Skill 被策略过滤，需要用户确认后重试 | `{ task_id, pipeline_run_id, stage_id, skills }` |
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

`type` 也支持 `eval_events` / `evaluation`，用于导出结构化执行反馈事件。

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
