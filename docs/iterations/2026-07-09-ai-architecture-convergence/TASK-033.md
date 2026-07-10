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
status: done
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

- [x] 设计 EvalEvent 表。
- [x] 新增 EvaluationService。
- [x] StageRuntime 记录 stage_started、stage_completed、stage_failed。
- [x] SkillDispatcher 记录 skill_called、skill_succeeded、skill_failed。
- [x] StageRuntime 记录阶段 AgentProfile、ModelRoute 与耗时。
- [x] DeliveryService 记录 delivery_succeeded、delivery_failed。
- [x] 新增 Evaluation API。
- [x] Dashboard 增加基础概览。
- [x] ExportManager 支持 EvalEvent JSONL 导出。

## 实现摘要

- 新增 `EvalEvent` 模型和 `019_eval_events.py` 迁移，记录项目、PipelineRun、Stage、Agent、ModelRoute、Skill、Artifact、Delivery、耗时、成本、失败原因和扩展 metadata。
- 新增 `EvaluationService.record_event()` 与 `safe_record_event()`；主链路打点使用独立 session，写入失败只记录日志，不阻断阶段执行、Skill 调用或交付。
- `StageRuntime` 在阶段启动、完成、失败和 Artifact 创建时记录结构化事件。
- `SkillDispatcher` 在 Skill 调用、成功、失败、超时和权限拒绝路径记录结构化事件。
- 本地写回、GitHub PR、zip Delivery 在成功、确认缺失、目标变更和异常路径记录交付事件。
- 新增 `/api/v1/evaluation/summary`，支持按 `project_id`、`pipeline_run_id`、时间范围过滤，并按当前登录用户做项目隔离。
- Dashboard 返回 `evaluation` 基础指标；导出类型 `eval_events` / `evaluation` 可生成 EvalEvent JSONL。

## 验收标准

- Eval 写入失败不能导致主流程失败，但必须有日志。
- 查询接口能按 project_id、pipeline_run_id、date range 过滤。
- Dashboard 不因无数据报错。
- 导出 JSONL 可包含 EvalEvent。

## 验证

```bash
uv run --extra dev pytest -q tests/api/test_evaluation.py tests/api/test_dashboard.py tests/api/test_exports.py tests/api/test_delivery.py tests/api/test_github_delivery.py tests/api/test_zip_delivery.py tests/skills/test_dispatcher.py tests/pipeline/test_runtime.py
```

```bash
npm run build
```

```bash
PYTHONPATH=/Users/yangkl/AgentForge/.worktrees/task-033-eval-feedback/src JWT_SECRET_KEY=task033-startup-secret uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18098
```

前端命令在 `/Users/yangkl/AgentForge/web` 下执行。
