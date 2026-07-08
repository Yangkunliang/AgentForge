# TASK-024：GitHub PR Delivery

**状态**：todo
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

- [ ] 设计并实现 GitHub PR preview，展示目标文件 diff、base branch、目标 branch 和 PR 摘要
- [ ] apply 时二次校验 base ref 未变化，变化时拒绝创建 commit 并写失败报告
- [ ] 创建远程 branch、commit 和 PR，PR body 附带 Artifact、Delivery report 和回滚说明
- [ ] 失败时按阶段记录 `delivery_status=failed`，必要时清理未引用 branch
- [ ] AuditLog 覆盖 preview、confirm denied、branch created、commit created、PR created、conflict、failed
- [ ] 使用 fake GitHub client 写后端测试，避免单测调用真实 GitHub API
- [ ] 前端 Artifact Viewer 支持选择 GitHub PR Delivery

## acceptance

- [ ] PR Delivery 不绕过用户确认
- [ ] base ref 变化不会覆盖远程内容
- [ ] token 不进入日志、审计 details 或前端响应
- [ ] 用户能从 Delivery report 找到 PR URL、commit sha 和恢复建议

## 不做

- 不实现 GitHub App installation 流程。
- 不自动 merge PR。
- 不支持跨 repo 批量 PR。
