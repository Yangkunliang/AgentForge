# TASK-024：GitHub PR Delivery

**状态**：done
**优先级**：P1
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-STRENGTHENING
**依赖**：TASK-023

## 目标

基于已授权的 GitHub Mount，把 Artifact 以 branch + commit + Pull Request 的方式交付到远程仓库，并保持 preview、确认、失败报告和审计链路。

## related_requirements

- CDW-07：结果回到项目
- CDW-08：写回必须可审计、可解释、可恢复
- CDW-10：交付方式覆盖本地、远程和兜底上传

## 技术子项

- [x] 设计并实现 GitHub PR preview，展示目标文件 diff、base branch、目标 branch 和 PR 摘要
- [x] apply 时二次校验 base ref 未变化，变化时拒绝创建 commit 并写失败报告
- [x] 创建远程 branch、commit 和 PR，PR body 附带 Artifact、Delivery report 和回滚说明
- [x] 失败时按阶段记录 `delivery_status=failed`，必要时清理未引用 branch
- [x] AuditLog 覆盖 preview、confirm denied、branch created、commit created、PR created、conflict、failed
- [x] 使用 fake GitHub client 写后端测试，避免单测调用真实 GitHub API
- [x] 前端 Artifact Viewer 支持选择 GitHub PR Delivery

## acceptance

- [x] PR Delivery 不绕过用户确认
- [x] base ref 变化不会覆盖远程内容
- [x] token 不进入日志、审计 details 或前端响应
- [x] 用户能从 Delivery report 找到 PR URL、commit sha 和恢复建议

## 实现结果

- 后端新增 `POST /api/v1/artifacts/{artifact_id}/delivery/github/preview` 和 `POST /api/v1/artifacts/{artifact_id}/delivery/github/apply`。
- `apply` 必须显式传入 `confirm_write=true` 和 preview 返回的 `expected_base_sha`；远程 base branch sha 改变时返回 409，不创建 branch、commit 或 PR。
- GitHub OAuth token 只从服务端 `OAuthCredential` 解密后传给 GitHub client；API 响应、Delivery report 和 AuditLog details 均不包含明文 token。
- 成功交付会在 Artifact 上保存 `delivery_channel=github_pr`、`pr_url`、`commit_sha`、base/target branch 和恢复提示。
- Artifact Viewer 新增“本地写回 / GitHub PR”交付方式切换，GitHub 模式支持 base branch、交付分支和 PR 标题输入。

## 验证

- `uv run --extra dev pytest tests/api/test_github_delivery.py`
- `uv run --extra dev pytest tests/api/test_delivery.py tests/api/test_github_delivery.py tests/api/test_github_mount.py`
- `npm run build`
- `npm run test:e2e -- artifact-viewer.spec.ts --project=chromium`

## 不做

- 不实现 GitHub App installation 流程。
- 不自动 merge PR。
- 不支持跨 repo 批量 PR。
