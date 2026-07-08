# TASK-022：交付能力扩展设计与实现

**状态**：todo
**优先级**：P2
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-STRENGTHENING
**依赖**：TASK-021

## 目标

在本地 Mount 可信交付稳定后，扩展更贴近真实开发团队的交付方式：GitHub 远程仓库、PR、zip 包和上传文件兜底，让 AgentForge 不只服务本机目录，也能服务多仓库和远程协作场景。

## related_requirements

- CDW-02：代码库访问必须用户主动授权
- CDW-07：结果回到项目
- CDW-10：交付方式覆盖本地、远程和兜底上传

## 技术子项

- [ ] 设计 GitHub OAuth Mount 的授权、scope 和 token 存储边界
- [ ] 设计 GitHub PR Delivery 流程：branch、commit、PR body、失败回滚
- [ ] 设计 zip 交付包导出，支持多文件 Artifact 或目录结构
- [ ] 设计 upload Mount，作为无法连接本地/GitHub 时的上下文兜底
- [ ] 根据设计拆分后续可独立验收的实现任务

## acceptance

- [ ] 远程交付不绕过用户授权
- [ ] PR/zip/upload 的数据流、API、失败状态和审计点清楚
- [ ] 后续实现任务可以逐个完成、提交、合并，不依赖一次性大改

## 不做

- 不在 TASK-022 之前抢跑 GitHub 写入。
- 不把 OAuth token 暴露给前端。
- 不自动扫描用户组织或仓库。
