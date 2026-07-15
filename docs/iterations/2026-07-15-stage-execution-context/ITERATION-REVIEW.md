# TASK-047 迭代复盘：StageExecutionContext

## 完成内容

- `StageDefinition` 增加 `required_input_artifact_types` 和 `success_criteria`，Catalog API 同步暴露阶段输入、输出和完成标准。
- 新增 `StageExecutionContext`，严格按当前 Project、PipelineRun 和真实阶段顺序读取前序 Artifact。
- 同一阶段同类型只选择最新 Artifact；上下文最多 6 项、单项 4000 字符、总计 12000 字符，并在入选项之间公平分配总预算。
- StageRuntime 把可信阶段元数据注入 system prompt；Artifact 正文以 `trust_level="untrusted"` 的 user-level reference 注入，并转义边界字符。
- tool-use、无工具直接回复、工具结果后最终回复三条路径共享同一阶段上下文。
- Artifact 类型事实源收敛到 Pipeline Catalog；完成归档异常会将 Stage 和 PipelineRun 置为 `failed`，不再滞留 `running`。

## TDD 与评审

实现过程先观察到以下红灯，再完成最小修正：

- Catalog 缺少阶段输入和完成标准。
- StageExecutionContext 模块及运行时注入不存在。
- 上游 Artifact 正文混入可信指令路径。
- 六项大 Artifact 的总预算被前几项耗尽。
- 修订后的最新 Artifact 被旧版本挤占。
- Artifact 持久化异常后 Stage 仍为 `running`。

独立代码评审发现最后两个阻断问题；修正后相关测试全部通过，未保留 Critical 或 Important 问题。

## 验证证据

- TASK-047 相关测试：`26 passed`。
- 后端全量：`352 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 生产代码 Ruff `E/F/I`（忽略目标文件既有 `E501` 长行）：通过。
- FastAPI：到达 `AgentForge startup complete` 和 `Application startup complete`；sandbox 禁止绑定 `127.0.0.1:18147`，随后完成正常 shutdown。该结果证明启动生命周期通过，不代表端口可访问测试通过。

此前一次全量测试出现大面积数据库错误，根因是主测试与独立评审测试并发共享固定 `test_db.sqlite`；停止并发后全量通过。后续不应在同一 worktree 并发执行 pytest。

## 残余风险

- `missing_input_artifact_types` 当前是提示，不是硬门禁；由 TASK-051 VerificationGate 收敛。
- 不可信标签和 Prompt 分层可降低指令混淆，但 Artifact 内容仍会概率性影响模型；SkillPolicy、Governance 和 Dispatcher 权限校验继续承担执行边界。
- 当前每阶段只归档一个 Markdown Artifact，多输出拆分仍未实现。
- Dashboard Task、费用和最近任务存在多租户过滤风险，由 TASK-048 作为下一项 P0 修复。
