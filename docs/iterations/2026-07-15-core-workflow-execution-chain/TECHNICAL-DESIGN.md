# 核心迭代工作流执行链技术蓝图

## 目标链路

```text
UserRequest
  -> IntentDecision
  -> PipelineRun
  -> StageExecutionContext
  -> TaskGraph
  -> WorkspaceExecutor
  -> VerificationGate
  -> Artifact / Delivery
  -> Eval Feedback
```

`PipelineOrchestrator` 负责状态推进和恢复，不承载具体代码执行；`StageRuntime` 负责解析当前阶段运行契约；`SkillExecutionEngine` 负责受治理的模型与工具循环；`WorkspaceExecutor` 只操作已授权 Mount；`VerificationGate` 只根据结构化命令结果决定阶段能否完成。

## 任务边界

| 任务 | 输入 | 输出 | 明确不做 |
|---|---|---|---|
| TASK-047 | PipelineRun、StageDefinition、Artifact | StageExecutionContext | 不执行代码、不自动推进阶段 |
| TASK-048 | 当前用户、Dashboard 查询 | 用户隔离统计 | 不改 LLM 聚合语义 |
| TASK-049 | task_split StageExecutionContext | TaskGraph / TaskNode | 不直接写工作区 |
| TASK-050 | TaskNode、ProjectMount 授权 | FilePatch / ApplyReport | 不自行判定测试通过 |
| TASK-051 | TaskGraph、Mount、测试策略 | VerificationRun / GateDecision | 不绕过人工确认 |
| TASK-052 | StageState、Confirmation、GateDecision | 下一状态和恢复点 | 不实现具体 Skill |
| TASK-053 | 完整运行时 API 和页面 | E2E 证据与 UX 收敛 | 不新增第二套运行时 |

## 横切约束

- Project 和 user_id 始终参与数据边界校验。
- Artifact、TaskGraph、Patch、VerificationRun 都记录来源和关联 id。
- 上游 Artifact 内容属于不可信数据，不进入 system prompt 的可信指令区。
- 所有上下文有数量、单项长度和总长度上限。
- 每项任务先红灯测试，再最小实现，再完整回归。
