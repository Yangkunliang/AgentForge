# TASK-023：GitHub OAuth Mount 授权底座

**状态**：todo
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

- [ ] 新增服务端 GitHub OAuth start/callback API，校验 state 并绑定当前用户
- [ ] 新增服务端加密凭证存储，不把 access token 放进 `ProjectMount.metadata`
- [ ] 创建 GitHub Mount 时只保存 repo 标识、默认分支、credential 引用和权限摘要
- [ ] 前端 Mount 创建流程支持选择 GitHub 连接方式，并展示授权状态
- [ ] 后端测试覆盖 state 校验、token 不下发前端、跨用户隔离和 revoke/断开连接

## acceptance

- [ ] GitHub Mount 必须由当前用户显式授权创建
- [ ] 前端 API 响应不包含 OAuth token
- [ ] AuditLog 记录授权、断开和失败，不记录 token
- [ ] 未授权 repo 不能被 PR Delivery 使用

## 不做

- 不创建 commit 或 PR。
- 不自动扫描用户组织下所有仓库。
- 不把 OAuth token 存入普通 JSON metadata。
