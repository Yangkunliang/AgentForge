# 核心能力增强技术设计

**日期**：2026-07-08
**关联架构**：`docs/architecture/CORE-DEV-WORKFLOW.md`
**状态**：方案设计

## 1. 总体策略

TASK-020 至 TASK-022 是核心闭环完成后的增强阶段。它不改变主链路：

```text
Project -> Mount -> Session -> PipelineRun -> StageState -> Artifact -> Delivery
```

增强顺序按风险排序：先加固 Delivery 写回可信度，再优化用户交互，最后扩展远程和打包交付。

## 2. TASK-020 服务端可信交付

### 2.1 Preview fingerprint

Delivery preview 读取目标文件时生成 fingerprint：

```text
exists
size
mtime_ns
sha256
```

其中 `sha256` 代表用户预览时看到的目标文件内容。目标不存在时 `exists=false` 且 `sha256=null`。

### 2.2 Apply consistency check

Delivery apply 增加可选 `expected_target_hash`：

```text
POST /api/v1/artifacts/{artifact_id}/delivery/apply
{
  "mount_id": "...",
  "target_path": "src/main.py",
  "confirm_write": true,
  "expected_target_hash": "<preview report target sha256>"
}
```

如果请求提供了 hash，服务端会在写入前重新读取目标 fingerprint。当前 hash 与 expected 不一致时，拒绝写入，返回 409，并将 Artifact 标记为 `failed`，保存失败报告。

### 2.3 Failure report

失败报告写入 `Artifact.delivery_report`：

```text
status
phase
target_path
mount_id
error_code
error_message
recovery_hint
target_fingerprint
```

报告目标是给用户明确解释“为什么没有写入”和“下一步怎么恢复”，而不是只返回 HTTP 错误。

### 2.4 AuditLog

Delivery 路由写入审计日志：

```text
delivery.preview.succeeded
delivery.apply.denied
delivery.apply.succeeded
delivery.apply.conflict
delivery.apply.failed
```

`details` 包含 artifact、project、mount、target_path、backup_path、fingerprint、error 等信息。审计日志不记录 Artifact 内容。

### 2.5 Startup hardening

本地 FastAPI 启动不得默认创建远程 E2B 沙箱。`init_sandbox_pool()` 只在 `SANDBOX_POOL_PREWARM_ENABLED=true` 时 bootstrap；默认情况下保留冷启动路径，首次 code executor 调用时再创建沙箱。

## 3. TASK-021 交互设计复盘

UI 复盘只解决核心工作流入口，不做视觉重写。重点对象：

- Project 首页：当前项目状态、Mount 健康、进行中 Pipeline、最近 Artifact。
- Chat：空状态、阶段状态、确认卡片、阶段完成卡片。
- Artifact Viewer：从查看、复用到交付的动作顺序。
- Delivery 面板：preview/apply 冲突或失败时的恢复提示。

## 4. TASK-022 交付扩展

GitHub / zip / upload 交付都必须遵守 Mount 主动授权原则。TASK-022 不直接实现写远程仓库，而是定义后续实现任务边界。

### 4.1 GitHub OAuth Mount

GitHub Mount 是 ProjectMount 的远程仓库授权形态：

```text
Project
  -> ProjectMount(mount_type=github, role=primary/reference)
    -> CredentialRef(encrypted OAuth token, server-only)
```

TASK-023 已落地授权底座：`oauth_states` 负责短期 state 绑定与一次性消费，`oauth_credentials` 负责服务端加密 token 存储；Project 创建向导选择 GitHub OAuth 时调用 start API 并传入项目专属 callback URI，完成页展示授权链接，callback 通过一次性 state 找回用户和项目，不依赖浏览器重定向携带 JWT header。

边界：

- `ProjectMount.metadata` 只保存非敏感信息：`repo_owner`、`repo_name`、`repo_full_name`、`default_branch`、`html_url`、`permission_summary`、`credential_id`。
- OAuth access token 必须进入服务端加密凭证表，前端响应、审计日志、Delivery report 都不得包含 token。
- OAuth `state` 必须绑定当前用户、Project、过期时间和 CSRF nonce。
- 客户端传入的 `redirect_uri` 必须指向当前 Project 的 AgentForge callback path。
- 授权完成后只创建用户显式选择的 repo Mount，不自动扫描组织或全部仓库。
- 如果 OAuth scope 难以做到单 repo 最小权限，产品上必须展示权限摘要；后续可切 GitHub App installation 获取更细粒度授权。

建议 API：

```text
POST /api/v1/projects/{project_id}/mounts/github/oauth/start
GET  /api/v1/projects/{project_id}/mounts/github/oauth/callback
DELETE /api/v1/projects/{project_id}/mounts/{mount_id}
```

审计事件：

```text
github_mount.oauth.started
github_mount.oauth.succeeded
github_mount.oauth.failed
github_mount.revoked
```

### 4.2 GitHub PR Delivery

TASK-024 已实现 PR Delivery。它复用 Delivery 的 preview/apply 两段式确认，但目标不是本地文件，而是 GitHub remote ref：

```text
Artifact -> GitHubDelivery.preview -> user confirm -> GitHubDelivery.apply
  -> create branch -> create/update files -> create commit -> create PR
```

preview 输入：

```text
artifact_id
mount_id
base_branch
target_branch
target_path
pr_title
```

preview 输出：

```text
base_sha
target_branch
target_path
unified_diff
pr_title
target_file_sha
```

apply 必须带 `expected_base_sha`。如果 base branch 当前 sha 与 preview 时不同，返回 409，保存失败报告，不创建 commit。

当前 API：

```text
POST /api/v1/artifacts/{artifact_id}/delivery/github/preview
POST /api/v1/artifacts/{artifact_id}/delivery/github/apply
```

失败处理：

| 阶段 | 失败处理 |
|------|----------|
| base ref 变化 | 拒绝 apply，`delivery_status=failed`，提示重新 preview |
| branch 创建失败 | 不写 commit，保存 GitHub 错误摘要 |
| commit 创建失败 | 若 branch 是本次新建且未被 PR 引用，可尝试删除 branch |
| PR 创建失败 | 保留 branch/commit，report 给出 commit sha 和手动建 PR 指引 |

审计事件：

```text
delivery.github.preview.succeeded
delivery.github.preview.failed
delivery.github.apply.denied
delivery.github.apply.branch_created
delivery.github.apply.commit_created
delivery.github.apply.pr_created
delivery.github.apply.conflict
delivery.github.apply.failed
delivery.github.apply.succeeded
```

Delivery report 字段：

```text
delivery_channel=github_pr
repo_full_name
target_path
delivery_target_path
base_branch
target_branch
base_sha
target_file_sha
pr_url
pr_number
commit_sha
commit_url
recovery_hint
```

安全约束：

- GitHub token 只从 `OAuthCredential` 服务端解密后传给 client。
- API 响应、Delivery report、AuditLog details 不记录明文 token 或 Artifact 正文。
- Artifact Viewer 在 preview 后从 `report.base_sha` 读取 expected base sha，确认创建 PR 时带回服务端。

### 4.3 zip Delivery Package

TASK-025 已落地该设计，对应 API 为：

```text
POST /api/v1/artifacts/{artifact_id}/delivery/zip/preview
POST /api/v1/artifacts/{artifact_id}/delivery/zip/apply
GET  /api/v1/artifacts/{artifact_id}/delivery/zip/download
```

zip Delivery 是不写用户目录、不调用远程 API 的交付兜底：

```text
Artifact -> ZipDelivery.preview -> ZipDelivery.apply -> downloadable package
```

zip 包必须包含：

```text
manifest.json
delivery-report.md
files/<relative paths>
```

路径规则：

- 包内路径必须是相对路径。
- 禁止绝对路径、空路径、`..`、反斜杠、Windows 盘符、控制字符和重复路径。
- `manifest.json` 记录 artifact、project、file_count、bytes、sha256。

状态：

- preview：只计算包结构和 sha256，不落下载文件。
- apply：生成 zip，保存下载引用、sha256、过期时间和 report。
- failed：写入失败报告，删除未完成临时文件。

实现约束：

- apply 必须显式 `confirm_write=true`，但 zip Delivery 不写本地目录、不调用远程仓库 API。
- 下载接口按 Artifact 所属 Project 校验用户权限，响应和 report 不暴露服务器临时路径。
- `DELIVERY_PACKAGE_DIR` 控制 zip 临时存储目录，`DELIVERY_PACKAGE_TTL_HOURS` 控制下载保留时间。
- 审计事件包括 `delivery.zip.preview.succeeded`、`delivery.zip.preview.failed`、`delivery.zip.apply.denied`、`delivery.zip.apply.succeeded`、`delivery.zip.apply.failed`。

### 4.4 Upload Mount

Upload Mount 是上下文读取兜底，不是写回目标：

```text
ProjectMount(mount_type=upload)
  -> uploaded file manifest
  -> Bridge list/read by manifest only
```

约束：

- 用户必须主动上传文件；平台不读取本地路径。
- `locator` 可以是服务端内部 upload collection id，不是用户机器路径。
- Bridge 读取必须限定在 manifest 中的相对路径。
- 单文件大小、总大小、文件数量、允许扩展名必须可配置。
- 删除 Upload Mount 时同步清理文件或标记过期。

审计事件：

```text
upload_mount.file.uploaded
upload_mount.file.read
upload_mount.deleted
upload_mount.failed
```

### 4.5 后续任务拆分

| 任务 | 范围 | 依赖 | 验收 |
|------|------|------|------|
| TASK-023 | GitHub OAuth Mount 授权底座 | TASK-022 | token 不下发前端，Mount 由用户显式授权创建 |
| TASK-024 | GitHub PR Delivery | TASK-023 | preview/apply、base sha 校验、PR URL、审计日志 |
| TASK-025 | zip Delivery Package | TASK-022 | 已完成：zip manifest、sha256、下载权限和过期清理 |
| TASK-026 | Upload Mount 上下文兜底 | TASK-022 | manifest 范围读取、路径安全、上下文选择器接入 |

## 5. 验证策略

- 服务端改动必须跑全量 `uv run --extra dev pytest`。
- FastAPI 路由、配置或依赖改动必须跑 uvicorn 启动检查。
- 迁移或模型相关改动必须跑 Alembic upgrade smoke。
- 前端改动必须跑 `npm run build`，涉及用户流程时补充 Playwright E2E。
