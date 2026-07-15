# TASK-050 实施计划：WorkspaceExecutor

## Task 1：设计与边界

- [x] 选定 WorkspaceChangeSet + FilePatch 持久化方案。
- [x] 固化 Project/TaskNode/Mount/Artifact 所有权与路径边界。
- [x] 固化 Preview、Apply、回滚、审计和后续任务契约。

Commit: `feat-设计授权工作区执行器迭代`

## Task 2：模型、迁移与 Preview

- [x] 红灯覆盖模型持久化、多文件 diff、target_files 和 Mount 边界。
- [x] 新增 WorkspaceChangeSet/FilePatch 与 021 migration。
- [x] 实现 preview service、序列化和 `POST .../workspace/preview`。
- [x] 实现 `GET /workspace-change-sets/{id}` 用户隔离读取。
- [x] 定向测试并提交。

Commit: `feat-实现工作区Patch预览`

## Task 3：Apply、回滚与治理

- [x] 红灯覆盖未确认、冲突、成功、幂等、failed 重试和写入异常回滚。
- [x] 实现全量基线预检、applying journal、文件写入和正常失败回滚。
- [x] 新增 workspace_write GovernanceDecision 和 AuditLog 事件。
- [x] 定向测试并提交。

Commit: `feat-实现工作区Patch确认应用`

## Task 4：验证、文档与集成

- [x] 执行定向和后端全量测试。
- [x] 执行生产代码 lint、migration heads 和 FastAPI 生命周期验证。
- [x] 代码评审无阻断问题。
- [x] 同步架构、数据库、API、安全、README、MEMORY、CLAUDE 和复盘。
- [x] 推送功能分支，合并并推送 `main`。

Commit: `feat-完成授权工作区执行器迭代`
