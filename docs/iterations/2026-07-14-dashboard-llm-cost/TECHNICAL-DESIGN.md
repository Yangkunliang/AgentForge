# TASK-046 技术设计

## 架构决策

继续以 `EvaluationService.get_summary()` 为成本与用量的唯一事实源。Dashboard 不直接查询 `EvalEvent`，也不从 `Task.total_cost_usd` 推导 LLM 成本，避免聚合语义分叉。

候选方案对比：

| 方案 | 优点 | 问题 | 结论 |
|------|------|------|------|
| 复用 `Task.total_cost_usd` | 改动最少 | 无法表达 ModelRoute / Stage，也不等同于真实 LLM 调用 | 不采用 |
| 新建成本聚合表 | 查询性能可控 | 当前数据量和需求不足以支撑额外写模型 | 暂不采用 |
| 扩展 Evaluation summary | 复用现有事件、权限和过滤能力 | 每次请求需要读取事件 | 本任务采用 |

## 数据契约

Evaluation summary 新增：

```json
{
  "llm_by_model_route": [
    {
      "model_route_key": "default",
      "name": "Default Route",
      "total_calls": 4,
      "tokens_used": 8200,
      "cost_usd": 0.084,
      "average_latency_ms": 640.0
    }
  ],
  "llm_by_stage": [
    {
      "stage_id": "backend_development",
      "name": "后端开发",
      "total_calls": 3,
      "tokens_used": 6100,
      "cost_usd": 0.061,
      "average_latency_ms": 590.0
    }
  ]
}
```

Dashboard `evaluation.llm` 映射为：

```text
total_calls
tokens_used
cost_usd
average_latency_ms
by_model_route[0..2]
by_stage[0..2]
```

## 聚合规则

- 输入事件限定为 `event_type.startswith("llm_")`。
- ModelRoute 以 `model_route_key` 分组；名称优先使用 `model_route_name`，缺失时回退 route key。
- Stage 以 `stage_id` 分组；名称优先使用事件 metadata 的 `stage_name`，缺失时回退 stage id。
- 排序顺序为 `cost_usd`、`tokens_used`、`total_calls` 降序，key 升序作为稳定兜底。
- 空值成本、token 和延迟分别按 0、0 和不参与平均值处理。
- Dashboard 只返回前 3 项，Evaluation summary 保留完整维度列表供其他消费者使用。

## 运行时补充

`StageRuntime` 构造 evaluation context 时增加非敏感的 `stage_name`；`SkillExecutionEngine` 将该字段写入 `llm_tool_use_completed.metadata.stage_name`。历史事件没有该字段时仍以 `stage_id` 展示。

## 边界与风险

- 当前聚合是请求时计算，数据规模显著增长后再评估数据库聚合或物化视图，不提前引入复杂度。
- TASK-045 仅覆盖非流式 tool-use 调用，页面标题和文档不宣称覆盖全部模型请求。
- 旧任务费用统计保持原行为，但 UI 明确标注为任务费用，避免与 EvalEvent LLM 成本混淆。
