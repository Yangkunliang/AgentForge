# 核心能力增强迭代复盘

**日期**：2026-07-08
**当前完成任务**：TASK-020、TASK-021、TASK-022、TASK-023、TASK-024、TASK-025、TASK-026
**结论**：服务端可信交付巩固、核心交互入口优化、交付扩展设计、GitHub OAuth Mount 授权底座、GitHub PR Delivery、zip Delivery Package 和 Upload Mount 上下文兜底已完成。

## 完成内容

### TASK-020

- Delivery preview 返回目标文件 fingerprint，包含 `exists`、`size`、`mtime_ns`、`sha256`。
- Delivery apply 支持 `expected_target_hash`，目标文件在预览后变化时返回 409，不覆盖用户文件。
- Delivery 写回冲突或 Bridge 失败时，Artifact 标记为 `delivery_status=failed`，并保存可读失败报告。
- Delivery preview、确认拒绝、成功、冲突和失败均写入 `AuditLog.resource=artifact_delivery`。
- Artifact Viewer 在确认写回时带上预览阶段的 target hash。
- FastAPI 默认启动不再预热远程 E2B 沙箱池；生产需要热池时显式设置 `SANDBOX_POOL_PREWARM_ENABLED=true`。

### TASK-021

- Project 首页新增下一步动作条，按 Mount 连接、进行中 PipelineRun、Artifact 数量提示用户下一步。
- Project 首页最近产物入口从无行为设置按钮调整为可直达 Artifact Viewer。
- Chat 空状态展示当前项目和代码库连接状态，快捷入口改为定位 Bug、开发新功能、迭代优化、UI 调整、架构与选型、代码 Review。
- StagePreview 新增当前阶段摘要，例如“当前：后端开发 · 运行中”。
- ConfirmCard 增加“查看产物并交付”入口；ArtifactCard 增加交付状态标签。
- 新增 `UI-REVIEW.md` 记录 UI/UX 复盘、设计约束和剩余风险。

### TASK-022

- GitHub OAuth Mount 设计明确：OAuth state 绑定用户/Project、token 服务端加密存储、ProjectMount metadata 不放敏感凭证。
- GitHub PR Delivery 设计明确：preview/apply 两段式、`expected_base_sha` 二次校验、branch/commit/PR 阶段化失败报告和审计事件。
- zip Delivery 设计明确：zip 包含 `manifest.json`、`delivery-report.md`、`files/`，路径必须是安全相对路径。
- Upload Mount 设计明确：只读取用户主动上传 manifest 内文件，不访问本地路径，也不作为写回目标。
- 拆出 TASK-023～TASK-026，分别覆盖 GitHub OAuth Mount、GitHub PR Delivery、zip Delivery Package、Upload Mount。

### TASK-023

- 新增 GitHub OAuth start/callback API，state 绑定当前用户、Project、provider、repo 和过期时间；callback 作为浏览器重定向路径，不依赖 Authorization header。
- start API 校验客户端传入的 `redirect_uri` 必须指向当前项目 callback path，防止 OAuth code 外带。
- 新增 `oauth_credentials` 与 `oauth_states` 数据模型和迁移；OAuth token 服务端加密存储，不进入 ProjectMount metadata。
- callback 成功后创建 connected GitHub Mount，metadata 仅保存 repo 标识、默认分支、权限摘要和 credential 引用。
- 删除 GitHub Mount 时标记关联 credential revoked，并写入 `github_mount.revoked` 审计。
- Project 创建向导选择 GitHub OAuth 时调用 OAuth start，完成页展示授权状态和授权链接，不再创建普通 GitHub Mount。

### TASK-024

- 新增 GitHub PR Delivery preview/apply API，复用 Artifact Delivery 的两段式确认语义。
- preview 读取 GitHub base branch sha 和目标文件内容，返回 unified diff、`base_sha`、目标分支和 PR 摘要，不创建远程状态。
- apply 必须带 `confirm_write=true` 与 `expected_base_sha`；base sha 变化时返回 409，Artifact 保存 `github_base_changed` 失败报告，不创建 branch、commit 或 PR。
- 成功 apply 后依次创建 branch、commit 和 PR，Delivery report 保存 `pr_url`、`commit_sha`、base/target branch 和恢复提示。
- GitHub client 通过 fake client 覆盖后端测试，单元测试不访问真实 GitHub API。
- Artifact Viewer 新增“本地写回 / GitHub PR”交付方式切换，GitHub 模式提交 `expected_base_sha` 并展示 PR URL / commit sha。

### TASK-025

- 新增 zip Delivery preview/apply/download API，作为不写本地目录、不调用远程仓库 API 的交付兜底。
- preview 计算包内路径、文件数量、总字节数和 deterministic zip sha256，不落地下载文件。
- apply 必须 `confirm_write=true`，生成 `manifest.json`、`delivery-report.md` 和 `files/<relative path>`，并保存 `delivery_channel=zip` 的 Delivery report。
- 下载接口按 Artifact 所属 Project 权限校验，不暴露服务器临时路径。
- 包内路径拒绝绝对路径、`..`、空路径、反斜杠、Windows 盘符、控制字符和重复路径。
- 新增过期 zip 清理配置 `DELIVERY_PACKAGE_DIR`、`DELIVERY_PACKAGE_TTL_HOURS`。
- Artifact Viewer 新增“zip 包”交付模式，可预览包信息、生成 zip 并下载。

### TASK-026

- 新增 Upload Mount multipart 上传 API，创建 connected upload Mount，并把 manifest 保存到 `ProjectMount.metadata`。
- manifest 记录相对路径、文件大小、MIME、sha256、storage_path 和上传时间，不保存文件正文。
- Bridge list/read 支持 upload Mount，读取范围严格限定在 manifest 内；Chat 上下文注入可读取 upload 文件。
- 上传路径拒绝绝对路径、`..`、反斜杠、Windows 盘符、控制字符和重复路径。
- 上传文件数量、单文件大小、总大小和允许扩展名通过 `UPLOAD_MOUNT_*` 配置控制。
- 删除 Upload Mount 时清理对应文件集合，并写入 `upload_mount.deleted` 审计。
- Project 创建向导的“手动上传”接入真实 API，ContextPicker 文件源支持 connected local/upload Mount。

## 发现并修正的风险

| 风险 | 修正 |
|------|------|
| 用户预览 diff 后，目标文件被外部修改仍可能被覆盖 | apply 支持 expected hash，冲突返回 409 并失败落库 |
| 写回失败只返回 HTTP 错误，不便追溯 | Artifact 保存失败报告，审计日志记录失败 details |
| 默认启动预热 5 个 E2B 云沙箱，增加本地成本和外部依赖 | 新增 `SANDBOX_POOL_PREWARM_ENABLED=false` 默认跳过预热 |
| Project、Stage、Artifact 数据分散，用户需要自行推断下一步 | Project next-action、Stage 摘要、ConfirmCard 交付入口和 Artifact 交付状态显性化 |
| Chat 空状态偏泛用 AI 助手，和全栈开发闭环不够贴合 | 改为当前项目工作台入口，快捷动作对齐需求类型路由 |
| 远程交付、zip、upload 容易混成一个大任务 | TASK-022 只做边界设计，并拆成 TASK-023～TASK-026 独立验收 |
| OAuth token 容易被误放进 Mount metadata 或前端响应 | 设计单独加密凭证引用，metadata 只保存非敏感 repo 信息 |
| GitHub 选项如果仍走普通 ProjectMount，会让“记录了仓库地址”被误认为“已经授权” | 创建向导改为调用 OAuth start，完成页显示待 GitHub 确认和授权链接 |
| 用户删除 GitHub Mount 后服务端凭据仍可能被后续 PR Delivery 误用 | DELETE Mount 标记 `OAuthCredential.revoked_at`，TASK-024 必须拒绝已撤销凭据 |
| GitHub OAuth callback 是浏览器重定向，真实请求通常没有 Authorization header | callback 改为通过一次性 state 找回 user_id/project_id，start 仍必须登录 |
| 客户端可控 redirect_uri 可能把 OAuth code 带到外部域名 | start API 只接受当前 Project 的 AgentForge callback path |
| GitHub 远程 base branch 在 preview 后变化可能导致覆盖或错 PR | apply 强制提交 `expected_base_sha` 并二次读取 base sha，变化时拒绝交付 |
| GitHub token 可能被错误写进交付报告或审计 | token 只在服务端解密后传给 client，测试断言响应和 AuditLog details 不包含明文 token |
| zip 包内路径如果直接信任 Artifact 元数据，可能产生 Zip Slip 风险 | 统一校验相对路径，拒绝绝对路径、`..`、反斜杠、Windows 盘符、控制字符和重复路径 |
| zip 下载如果暴露服务端临时路径，会泄露部署目录 | report 只保存 `download_url`、package id 和 sha256，下载接口内部解析文件路径 |
| zip 文件长期堆积会放大磁盘风险 | 新增 TTL 配置，并在 apply 前清理过期包 |
| Upload Mount 若保存本地路径，会让用户误以为平台在扫描机器 | `locator` 只保存 `upload://<upload_id>`，Bridge 只读服务端 manifest |
| 上传文件正文进入审计会泄露代码或需求 | 审计 details 只记录路径、大小、sha、状态，不记录正文 |
| upload Mount 被误用为写回目标 | Delivery 写回仍通过 local-only 校验，upload 只参与 Bridge/Chat 只读上下文 |

## 验证结果

- `uv run --extra dev pytest tests/skills/test_code_executor_pool.py tests/api/test_delivery.py -q`：7 passed
- `uv run --extra dev pytest`：278 passed, 6 skipped, 11 xfailed
- `npm run build`：通过，保留既有 Sass deprecation 和 chunk size warning
- `npm run test:e2e -- artifact-viewer.spec.ts`：3 passed
- `DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:15432/agentforge uv run --extra dev alembic -c migrations/alembic.ini upgrade head`：通过，使用临时 `pgvector/pgvector:pg15` 容器
- `PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18086`：启动到 `AgentForge startup complete ✓`，日志显示 `SandboxPool warmup skipped`
- `npm run test:e2e -- projects.spec.ts human-confirmation.spec.ts pipeline-stage-state.spec.ts --project=chromium`：7 passed
- `git diff --check`：TASK-022 文档变更通过
- `uv run --extra dev pytest tests/api/test_github_mount.py`：6 passed
- `npm run test:e2e -- projects.spec.ts --project=chromium`：4 passed
- `uv run --extra dev pytest tests/api/test_github_delivery.py`：4 passed
- `uv run --extra dev pytest tests/api/test_delivery.py tests/api/test_github_delivery.py tests/api/test_github_mount.py`：15 passed
- `npm run test:e2e -- artifact-viewer.spec.ts --project=chromium`：4 passed
- `uv run --extra dev pytest tests/api/test_zip_delivery.py`：5 passed
- `npm run build`：通过，保留既有 Sass deprecation 和 chunk size warning
- `uv run --extra dev pytest tests/api/test_upload_mount.py`：5 passed
- `uv run --extra dev pytest tests/api/test_upload_mount.py tests/api/test_projects.py tests/api/test_delivery.py tests/api/test_zip_delivery.py`：24 passed
- `npm run test:e2e -- projects.spec.ts bridge-context.spec.ts --project=chromium`：7 passed

## 下一步

- 本轮 TASK-020～TASK-026 已形成可信交付、远程 PR、zip 和 upload 上下文兜底闭环；后续可继续做多 Mount 编排、发布策略和长期文件保留策略。
