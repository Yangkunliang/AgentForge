# 核心能力增强迭代复盘

**日期**：2026-07-08
**当前完成任务**：TASK-020、TASK-021、TASK-022、TASK-023
**结论**：服务端可信交付巩固、核心交互入口优化、交付扩展设计和 GitHub OAuth Mount 授权底座已完成，下一步进入 TASK-024 GitHub PR Delivery。

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

## 下一步

- TASK-024：在 TASK-023 之后实现 GitHub PR Delivery。
- TASK-025：实现 zip Delivery Package。
- TASK-026：实现 Upload Mount 上下文兜底。
