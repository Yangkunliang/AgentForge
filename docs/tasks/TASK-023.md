# TASK-023：GitHub OAuth Mount 授权底座

**状态**：done
**优先级**：P1
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-STRENGTHENING
**依赖**：TASK-022

## 目标

让用户可以主动授权 GitHub 仓库作为 `ProjectMount(mount_type=github)`，为后续 PR Delivery 提供只读 repo 元数据、branch/ref 查询和安全凭证引用。

## related_requirements

- CDW-02：代码库访问必须用户主动授权
- CDW-10：交付方式覆盖本地、远程和兜底上传

## 技术子项

- [x] 新增服务端 GitHub OAuth start/callback API，校验 state 并绑定当前用户
- [x] 新增服务端加密凭证存储，不把 access token 放进 `ProjectMount.metadata`
- [x] 创建 GitHub Mount 时只保存 repo 标识、默认分支、credential 引用和权限摘要
- [x] 前端 Mount 创建流程支持选择 GitHub 连接方式，并展示授权状态
- [x] 后端测试覆盖 state 校验、token 不下发前端、重复 state 拒绝和 revoke/断开连接

## acceptance

- [x] GitHub Mount 必须由当前用户显式授权创建
- [x] 前端 API 响应不包含 OAuth token
- [x] AuditLog 记录授权、断开和失败，不记录 token
- [x] 未授权 repo 不能被 PR Delivery 使用

## 实现记录

- 新增 `oauth_credentials` 与 `oauth_states`，OAuth token 通过 `agent_forge.security.credentials` 服务端加密保存。
- `POST /projects/{project_id}/mounts/github/oauth/start` 创建 10 分钟有效 state，并生成 GitHub 授权链接。
- start API 会校验客户端传入的 `redirect_uri` 必须指向当前项目的 AgentForge callback path，避免 OAuth code 被带到外部域名。
- `GET /projects/{project_id}/mounts/github/oauth/callback` 作为 GitHub 浏览器重定向路径，不要求 Authorization header；后端通过一次性 state 校验 Project、provider 和过期时间后创建 connected GitHub Mount。
- GitHub Mount metadata 只保存 `repo_owner`、`repo_name`、`repo_full_name`、`default_branch`、`html_url`、`permission_summary`、`credential_id`。
- 删除 GitHub Mount 时会标记关联 `OAuthCredential.revoked_at` 并写入 `github_mount.revoked` 审计。
- Project 创建向导选择 GitHub OAuth 时会调用 OAuth start，不再创建普通 pending GitHub Mount，并在完成页展示授权状态和授权链接。

## 验证

- `uv run --extra dev pytest tests/api/test_github_mount.py`：6 passed
- `npm run test:e2e -- projects.spec.ts --project=chromium`：4 passed

## 不做

- 不创建 commit 或 PR。
- 不自动扫描用户组织下所有仓库。
- 不把 OAuth token 存入普通 JSON metadata。
