# TASK-049 产品需求：结构化 TaskGraph

## 背景

`task_split` 阶段当前只生成 Markdown `report` Artifact。后续开发阶段无法稳定知道任务依赖、目标文件、验收标准和验证命令，也无法判断哪些任务可并行或是否全部完成。

现有 `Task` 表表示用户的一次请求；`SubTask` 属于旧 Executor 的简单拆分，缺少 Project、PipelineRun、依赖边和工程验收契约，不能与流水线 TaskGraph 混用。

## 用户目标

全栈开发工程师确认需求和架构后，AgentForge 能生成可查看、可追溯、可被执行器直接消费的任务图，而不是只能阅读一段任务列表文本。

## 范围

- 新增 PipelineRun 级 `TaskGraph`。
- 每个 `TaskNode` 包含稳定 key、标题、描述、目标文件、验收标准和验证命令。
- 依赖关系使用结构化边保存，并拒绝不存在依赖、自依赖和环。
- `task_split` 使用严格 `task_graph_v1` JSON 输出契约。
- 结构化图与可读 Markdown Artifact 在同一事务创建。
- 提供当前用户隔离的 TaskGraph 读取 API。

## 非目标

- 不修改工作区文件；由 TASK-050 WorkspaceExecutor 负责。
- 不执行验证命令；由 TASK-051 VerificationGate 负责。
- 不自动调度节点或推进 Pipeline；由 TASK-052 PipelineOrchestrator 负责。
- 不迁移旧 `SubTask` 数据。

## 验收标准

1. 合法 DAG 可原子持久化并通过 API 读取。
2. 重复 key、未知依赖、自依赖、循环依赖和不安全目标路径被拒绝。
3. 非 JSON 或不符合 schema 的 task_split 输出使阶段失败，不产生 Artifact 或半成品 TaskGraph。
4. 其他用户不能读取当前用户的 TaskGraph。
5. Artifact 保留人类可读任务摘要，并关联 TaskGraph id。
