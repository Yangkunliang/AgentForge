# TASK-045 技术设计：LLM 成本评估事件

## 数据流

```text
StageRuntime
  -> SkillExecutionEngine.run(advanced_context.eval / agent_profile / model_route)
  -> llm.tool_use_complete(messages, tools, config)
  -> LLMResponse(tokens_used, cost_usd, latency_ms)
  -> EvaluationService.safe_record_event(event_type=llm_tool_use_completed)
  -> EvaluationService.get_summary().llm
```

## 事件定义

`llm_tool_use_completed` 写入字段：

| 字段 | 来源 |
|------|------|
| `project_id` | `advanced_context.eval.project_id` |
| `pipeline_run_id` | `advanced_context.eval.pipeline_run_id` |
| `stage_id` | `advanced_context.eval.stage_id` |
| `agent_profile_id/name` | `advanced_context.agent_profile` |
| `model_route_key/name` | `advanced_context.model_route` |
| `model_name` | `LLMResponse.model`，为空时退回 `model_route.model_name` |
| `latency_ms` | `LLMResponse.latency_ms` |
| `cost_usd` | `LLMResponse.cost_usd` |
| `tokens_used` | `LLMResponse.tokens_used` |

`metadata_json` 仅记录执行形态：

```json
{
  "call_type": "tool_use_complete",
  "round": 1,
  "tools_visible": 3,
  "has_tool_calls": true,
  "tool_call_names": ["web_search"]
}
```

## 安全边界

- 不记录 prompt、messages、用户输入、源码文件正文、工具返回正文或 credential secret。
- Evaluation 写入失败使用 `safe_record_event()` 吞掉异常并记录 warning，不阻断主链路。
- 缺少 `advanced_context.eval` 时跳过事件，避免脱离 Project / Pipeline 的独立调用污染评估数据。

## Summary 变化

`GET /api/v1/evaluation/summary` 新增：

```json
{
  "llm": {
    "total": 2,
    "succeeded": 2,
    "failed": 0,
    "success_rate": 1.0,
    "average_latency_ms": 500.0,
    "cost_usd": 0.03,
    "tokens_used": 350
  }
}
```

`agents` 和 `models` 维度继续按 EvalEvent 聚合，并补充 `tokens_used`，便于按 Agent / ModelRoute 看总 token。

## 后续增强

- `stream_complete` 的 usage 返回需等流式 provider 能提供可靠 usage 后再接。
- 可在 Dashboard 上新增 LLM 成本趋势和高成本阶段排行。
- 可把 budget_policy 接入 GovernancePolicy，按 Project / Stage / ModelRoute 做预算确认或拦截。
