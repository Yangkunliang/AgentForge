# TASK-047 产品需求：阶段执行上下文

## 问题

当前 StageRuntime 会读取 StageDefinition 来选择 Agent、ModelRoute 和 SkillPolicy，但 SkillExecutionEngine 看不到当前阶段名称、目标、必需输入、预期产物和完成标准。上一阶段 Artifact 也没有结构化进入下一阶段，执行主要依赖最近 20 条聊天消息，导致不同阶段可能生成相似回答，需求分析、架构设计、开发和测试之间缺少可验证的语义连接。

## 用户价值

全栈开发工程师在运行流水线时，应看到每个阶段基于已经确认的上游产物继续工作，而不是反复解释需求。阶段输出应匹配 Catalog 声明的产物类型，并能说明当前缺少哪些输入。

## 范围

- StageDefinition 增加必需输入产物类型和完成标准。
- StageRuntime 构造有界的 StageExecutionContext。
- 上游 Artifact 只从当前用户已授权 PipelineRun 的前序阶段加载。
- SkillExecutionEngine 把可信阶段指令与不可信 Artifact 内容分层传给模型。
- StageRuntime 创建 Artifact 时以 Pipeline Catalog 的输出类型为事实源。

## 非目标

- 不创建 TaskGraph。
- 不执行或应用代码 Patch。
- 不运行真实测试命令。
- 不自动推进确认后的下一阶段。
- 不新增数据库表或迁移。

## 验收标准

- 当前阶段的 id、名称、目标、顺序、输入类型、输出类型和完成标准进入执行上下文。
- 只加载同 Project、同 PipelineRun、当前阶段之前的 Artifact；其他用户、其他 Run、当前/未来阶段均不进入。
- 上游 Artifact 最多 6 个，单项内容最多 4000 字符，总内容最多 12000 字符，并标记截断状态。
- 缺失输入类型进入 `missing_input_artifact_types`，本任务只提示，不阻断执行。
- Artifact 内容不进入 system prompt，且以 `trust_level="untrusted"` 包裹并转义边界字符。
- 实际创建的 Artifact 类型来自 StageDefinition，不再依赖独立硬编码映射。
- 相关回归、后端全量测试和 FastAPI 生命周期验证完成。
