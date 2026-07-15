# TASK-049 迭代复盘：结构化 TaskGraph

## 完成内容

- Catalog 的 `task_split` 声明 `output_contract_key=task_graph_v1`，StageExecutionContext 与可信 system prompt 同步暴露输出合同。
- 新增严格 JSON parser、Pydantic schema、DAG 校验和安全相对路径校验。
- 新增 `TaskGraph`、`TaskNode`、`TaskNodeDependency` 与 `020_task_graph` 迁移，一个 PipelineRun 最多一个图。
- StageRuntime 缓冲结构化输出，在同一事务内创建可读 Markdown Artifact、TaskGraph、节点和依赖边；聊天只返回 Markdown，非法输出不泄漏部分 JSON、回滚并使 Stage/Run failed。
- 新增 `GET /api/v1/pipeline-runs/{run_id}/task-graph`，先校验 Run 所属用户，其他用户和无图场景均返回 404。

## 关键决策

- `Task` 继续表示用户请求，旧 `SubTask` 继续服务早期 Executor，均不复用为 TaskGraph 节点。
- TaskGraph 是 WorkspaceExecutor 和 VerificationGate 的机器可消费事实源；Artifact 是人类可读投影，不允许后续模块反向解析 Markdown。
- LLM 输出不直接进入执行器，必须先通过 schema、依赖、环和路径安全校验。
- 迁移中的结构化列表字段与模型一致：SQLite 使用 JSON，PostgreSQL 使用 JSONB，避免后续 schema drift。
- 当前图在 PipelineRun 内不可变且唯一，节点执行状态推进留给 TASK-050～TASK-052。

## 验证结果

- 定向回归：27 passed。
- 后端全量：366 passed、6 skipped、11 xfailed、41 warnings。
- 生产改动 E/F/I lint：通过。
- Alembic：`0020 (head)`，单一 head。
- FastAPI：完成 startup/shutdown 生命周期，`GET /api/v1/health` 返回 200；本机未启动 PostgreSQL、RabbitMQ、Redis，因此依赖状态为 degraded。

## 风险与后续

- `target_files` 当前只做语法安全校验，真实 ProjectMount 授权根和写入范围由 TASK-050 WorkspaceExecutor 强制执行。
- `verification_commands` 当前只保存，不执行；命令白名单、超时、退出码和报告由 TASK-051 VerificationGate 负责。
- 当前不支持同一 PipelineRun 修订或版本化多个 TaskGraph；若后续允许重新拆解，应新增显式 revision，而不是覆盖历史事实。
- 现有全量测试 warning 主要来自 Pydantic V2 兼容、pytest 未注册 mark 和异步 mock 基线，本任务未扩大这些告警。

## 集成记录

- 功能分支：`feature/task-049-task-graph`。
- 功能分支完成后已推送，并以 fast-forward 方式合并到 `main`。
- TASK-049 在 `main` 上的最终集成记录使用独立中文提交，便于后续路线图追溯。
