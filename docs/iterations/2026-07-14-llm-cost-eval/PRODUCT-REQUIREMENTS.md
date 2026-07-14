# TASK-045 产品需求：LLM 成本评估事件

## 背景

TASK-030 已让 StageRuntime 使用结构化 ModelRoute，TASK-033 已建立 EvalEvent，TASK-044 已把 Artifact 生成来源固化到 metadata。当前仍缺一段关键事实：LLM 路由决策调用已经拿到 token、cost 和 latency，但没有进入 Evaluation summary。

这会影响长期迭代：

- 无法按 Project / Pipeline / Stage 观察模型成本。
- 无法评估某个 ModelRoute 是否值得继续作为默认路由。
- Artifact 能展示来源，但缺少生成过程的成本事实。

## 目标

- 将 SkillExecutionEngine 中非流式 `tool_use_complete` 的 token、cost、latency 写入 EvalEvent。
- Evaluation summary 新增 `llm` 聚合块，便于 Dashboard、导出和后续策略优化消费。
- 保持事件 metadata 不包含 prompt、用户消息、源码正文或凭据。

## 不做

- 不改 EvalEvent 表结构。
- 不接入 `stream_complete` 的 token 统计；当前流式接口没有可靠 usage 返回，后续单独处理。
- 不新增前端 Dashboard 卡片。
- 不改模型选择策略或预算拦截策略。

## 验收标准

- SkillExecutionEngine 每次成功完成 `tool_use_complete` 后记录 `llm_tool_use_completed`。
- 事件包含 project、pipeline_run、stage、agent_profile、model_route、model_name、tokens_used、cost_usd、latency_ms。
- Evaluation summary 返回 `llm.total`、成功率、平均耗时、累计成本和累计 token。
- 相关测试、全量后端测试、前端构建和 FastAPI 启动验证通过。
