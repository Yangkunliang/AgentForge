# TASK-045 测试计划

## 红绿测试

- `tests/skills/test_engine_context.py::test_skill_engine_records_llm_tool_use_usage_event`
  - 红灯：`SkillExecutionEngine.__init__` 不支持注入 evaluation session factory，且不会写入 `llm_tool_use_completed`。
  - 绿灯：非流式 LLM 决策调用完成后写入 EvalEvent，字段和 metadata 与预期一致。
- `tests/api/test_evaluation.py::test_evaluation_service_summarizes_llm_usage`
  - 红灯：Evaluation summary 缺少 `llm` 块。
  - 绿灯：summary 聚合 total、success_rate、average_latency_ms、cost_usd 和 tokens_used。

## 回归范围

- `tests/skills/test_engine_context.py`
- `tests/api/test_evaluation.py`
- `tests/pipeline/test_runtime.py`
- 后端全量 pytest
- `web` 前端构建
- FastAPI uvicorn 启动

## 额外检查

- 确认 EvalEvent metadata 不包含 prompt / message / 文件内容。
- 确认无 `advanced_context.eval` 的独立 SkillEngine 调用不会写入孤儿事件。
- 确认 Evaluation 写入失败不阻断主链路。
