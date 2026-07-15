# TASK-049 实施计划：结构化 TaskGraph

## Task 1：设计与契约

- [x] 区分用户 Task、旧 SubTask 和 Pipeline TaskGraph。
- [x] 定义 task_graph_v1 JSON、DAG 校验和安全路径规则。
- [x] 定义原子持久化与读取 API。

Commit: `feat-设计结构化TaskGraph迭代`

## Task 2：输出契约与解析器

- [x] Catalog/StageExecutionContext 暴露 output_contract_key。
- [x] Engine 渲染 task_graph_v1 可信输出约束。
- [x] 实现 Pydantic spec、JSON parser、DAG/path 校验和 Markdown renderer。
- [x] 定向测试并提交。

Commit: `feat-实现TaskGraph输出契约`

## Task 3：模型、迁移与 Service

- [x] 新增 TaskGraph、TaskNode、TaskNodeDependency 模型。
- [x] 新增 020 migration 和模型导出。
- [x] 实现原子 create/load/serialize service。
- [x] 定向测试并提交。

Commit: `feat-持久化结构化TaskGraph`

## Task 4：Runtime 与 API

- [x] task_split 完成时先解析再创建 Artifact 和 TaskGraph。
- [x] 非法输出进入 failed 且无半成品。
- [x] 新增 `/pipeline-runs/{run_id}/task-graph` 用户隔离 API。
- [x] 定向测试并提交。

Commit: `feat-将TaskGraph接入流水线运行时`

## Task 5：验证、文档和集成

- [x] 执行定向和后端全量测试。
- [x] 执行生产代码 lint、迁移 heads 和 FastAPI 生命周期验证。
- [x] 代码评审无阻断问题，并修复用户可见原始 JSON 与 PostgreSQL JSONB 漂移风险。
- [x] 同步架构、数据库、API、README、MEMORY、CLAUDE 和复盘。
- [ ] 推送功能分支，合并并推送 `main`。

Commit: `feat-完成结构化TaskGraph迭代`
