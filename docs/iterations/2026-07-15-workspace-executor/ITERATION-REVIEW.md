# TASK-050 迭代复盘：授权 WorkspaceExecutor

## 完成内容

- 新增 `WorkspaceChangeSet`、`FilePatch` 和 `021_workspace_change_sets` 迁移，把 TaskNode 的多文件开发结果固化为不可覆盖版本。
- Preview 校验当前用户、Project、TaskGraph/TaskNode、connected local primary Mount、可选 Artifact 和 TaskNode.target_files，只读取基线并生成 diff，不写文件。
- Apply 通过 `workspace_write` GovernanceDecision、WorkspaceChangeSet 行锁和全部文件基线预检后写入；重复 Apply 幂等，failed 版本必须重新 Preview。
- 第二次逐文件基线检查覆盖预检后的竞争窗口；正常写入异常会按相反顺序恢复已尝试文件，并保存结构化 ApplyReport。
- 新增 Preview、查询和 Apply API；所有权错误返回 404，确认、冲突、成功、幂等和失败路径写入 `AuditLog.resource=workspace_change_set`。
- API、ApplyReport 和 AuditLog 不返回 `proposed_content` 或原文件正文；现有 Artifact Delivery 保持兼容，不复用 WorkspaceChangeSet 状态。

## TDD 与风险修正

- 红灯先覆盖多文件 Preview、路径越界、跨 Project/Mount、敏感路径和失败不留半成品。
- Apply 红灯覆盖未确认、成功、幂等、全量基线冲突、failed 重试和第二个文件写入失败后的反向回滚。
- 并发复核补充 PostgreSQL `FOR UPDATE OF workspace_change_sets` 合同和路由级断言，避免同一 ChangeSet 被并发应用。
- 合并前授权评审发现 Preview 后 Mount 状态、角色或 root 变化仍可能影响新文件 Patch；修正为封存 root sha256，并在 Apply 时复核 Mount 和 TaskNode 当前范围。
- Preview 先完成全部基线读取再创建 ORM 对象，失败审计提交时不会意外提交半成品 ChangeSet。

## 验证结果

- WorkspaceExecutor 与关联 Delivery/Project 定向回归：`30 passed`。
- 后端全量：`381 passed, 6 skipped, 11 xfailed, 43 warnings`。
- 本次生产代码 Ruff `E/F/I`：通过；`src/api/main.py` 的 `E501/F`：通过。
- Alembic：`0021 (head)`，单一 head。
- FastAPI：到达 `Application startup complete`；`GET /api/v1/health` 返回 HTTP 200。当前本机 PostgreSQL、RabbitMQ 未运行，健康状态为 `degraded`，Redis 为 `ok`；随后正常 shutdown，进程退出码 0。

## 残余风险与后续

- 数据库与本地文件系统不能组成同一 ACID 事务；进程在 `applying` journal 提交后崩溃时可能留下待核对状态。TASK-052 PipelineOrchestrator 应提供恢复扫描和人工处置入口。
- 第一版只支持 UTF-8 `upsert`，不支持删除、重命名、二进制文件和 GitHub Mount 写入。
- `proposed_content` 为完成写入而存入数据库，后续生产部署应把数据库备份、运维查询和数据保留策略纳入源码敏感数据治理。
- WorkspaceExecutor 不执行测试或构建，也不自行完成 TaskNode；TASK-051 VerificationGate 消费 applied ChangeSet 和 verification_commands，TASK-052 统一推进状态。
- 本任务只完成后端执行契约，面向终端用户的 Patch 预览、确认、失败恢复和验证结果交互由 TASK-053 收敛。

## 集成记录

- 功能分支：`feature/task-050-workspace-executor`。
- 完成功能分支验证后推送，并以 fast-forward 方式合并到 `main`。
- 功能分支最终提交 `6860c40` 已 fast-forward 合并到 `main`；`main` 使用独立中文集成提交补录路线图状态。
