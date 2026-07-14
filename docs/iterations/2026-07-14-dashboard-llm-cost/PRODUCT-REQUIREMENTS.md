# TASK-046 产品需求：Dashboard LLM 成本与用量

## 背景

TASK-045 已将非流式 `tool_use_complete` 的调用次数、token、成本和延迟写入 `EvalEvent`，并在 Evaluation summary 中提供 `llm` 聚合块。当前 Dashboard 仍只展示基于 `Task.total_cost_usd` 的任务费用，平台用户无法从页面判断真实模型调用的成本、用量和主要消耗来源。

## 用户目标

全栈开发工程师进入 Dashboard 后，可以快速回答：

- 当前账号累计发生了多少次已记录的 LLM 调用。
- 累计消耗多少 token 和成本，平均调用延迟是多少。
- 哪些 ModelRoute 和 Pipeline Stage 是主要成本来源。
- 当前没有 LLM 事件时，页面是否处于正常的零数据状态。

## 范围

- Evaluation summary 增加仅基于 `llm_*` 事件的 ModelRoute 和 Stage 聚合。
- Dashboard API 返回当前用户的 LLM 总览和前 3 项 ModelRoute / Stage 排行。
- Dashboard 页面增加 LLM 成本与用量区域。
- 旧费用卡改名为“任务费用（今日）”，与 LLM EvalEvent 成本明确区分。
- 新增后端回归测试和 Dashboard 浏览器 E2E。

## 不做

- 不采集 `stream_complete` usage；该能力属于 TASK-047。
- 不实现 `budget_policy` 确认或拦截；该能力属于 TASK-048。
- 不新增数据库表、物化视图或第三方 BI 依赖。
- 不把 prompt、用户消息、源码正文、工具输出或凭据写入统计结果。
- 不在本任务中改造既有任务、Agent、Skill 和最近任务统计口径。

## 验收标准

- Dashboard API 的 `evaluation.llm` 包含 `total_calls`、`tokens_used`、`cost_usd`、`average_latency_ms`、`by_model_route` 和 `by_stage`。
- ModelRoute / Stage 排行仅统计 `llm_*` EvalEvent，按成本降序排列，并限制为前 3 项。
- Dashboard 数据继续按当前登录用户隔离。
- 页面展示 LLM 调用、累计成本、Token、平均延迟和两类排行。
- 空数据时数值为 0，排行显示“暂无 LLM 调用记录”，页面不报错。
- 后端相关测试、后端全量测试、前端构建、Dashboard E2E 和 FastAPI 启动验证通过。
