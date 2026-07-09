# TASK-033: Eval Feedback 执行质量反馈闭环

```yaml
id: AIARCH-P1-007
module: evaluation
priority: P1
title: Eval Feedback 执行质量反馈闭环
related_requirements:
  - R-007
deliverable:
  - EvalEvent model and service
  - Evaluation summary API
  - Dashboard summary integration
  - Export integration
acceptance:
  - PipelineRun、Stage、Agent、Model、Skill、Delivery 关键事件能结构化记录
  - 能按项目和时间范围查询基础质量指标
  - 不影响主执行链路成功率
status: todo
```

## 背景

没有评估反馈，平台只能“凭感觉优化”。Eval Feedback 的第一版目标不是复杂打分，而是把执行事实结构化，让后续优化有数据基础。

## 范围

- 新增 EvalEvent 模型。
- 在 StageRuntime、SkillDispatcher、DeliveryService 写入关键事件。
- Evaluation API 返回项目维度摘要。
- Dashboard 展示基础指标。
- 导出能力支持 Eval 数据。

## 指标第一版

- PipelineRun 成功率。
- Stage 成功率和平均耗时。
- AgentProfile 使用次数和失败率。
- ModelRoute 使用次数、失败率、平均耗时、成本。
- Skill 调用次数、失败率、平均耗时。
- Artifact 生成数和交付状态。
- 人工确认次数和 revise 比例。

## 实施 checklist

- 设计 EvalEvent 表。
- 新增 EvaluationService。
- StageRuntime 记录 stage_started、stage_completed、stage_failed。
- SkillDispatcher 记录 skill_called、skill_succeeded、skill_failed。
- ModelRouter 或 LLM Provider 记录模型耗时和成本。
- DeliveryService 记录 delivery_succeeded、delivery_failed。
- 新增 Evaluation API。
- Dashboard 增加基础概览。

## 验收标准

- Eval 写入失败不能导致主流程失败，但必须有日志。
- 查询接口能按 project_id、pipeline_run_id、date range 过滤。
- Dashboard 不因无数据报错。
- 导出 JSONL 可包含 EvalEvent。

## 验证

```bash
uv run --extra dev pytest tests/api/test_dashboard.py tests/api/test_exports.py
```

```bash
uv run --extra dev pytest tests/api/test_evaluation.py
```

```bash
npm run build
```

前端命令在 `/Users/yangkl/AgentForge/web` 下执行。
