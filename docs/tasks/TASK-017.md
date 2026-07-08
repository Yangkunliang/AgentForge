# TASK-017：人工确认与阶段继续机制

**状态**：done
**优先级**：P1
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-015、TASK-016

**依赖状态**：TASK-015 已完成 PipelineRun / StageState / StageRuntime；TASK-016 已完成阶段 Artifact 归档、查看和上下文复用，确认节点可复用 Artifact 作为待确认内容。

## 目标

把 PRD 确认、技术选型确认、影响范围确认做成真实流程节点。Agent 在确认点必须暂停，用户确认或修改后才能继续。

## related_requirements

- CDW-05：关键节点人工确认

## 技术子项

- [x] StageState 支持 `waiting_confirmation`
- [x] 新增 `confirm_required` / `confirm_resolved` SSE 事件
- [x] ConfirmCard 接真实事件渲染
- [x] 新增确认 API：确认继续、提出修改意见、取消执行
- [x] StageRuntime 在确认前停止自动推进
- [x] 用户修改意见写入下一次同阶段执行上下文
- [x] 审计日志记录确认操作

## acceptance

- [x] PRD 阶段完成后触发确认卡片
- [x] 用户确认后进入下一阶段
- [x] 用户提出修改意见后同阶段重新执行或追加修订
- [x] 未确认时不会继续执行后续阶段
- [x] 确认操作有审计记录
- [x] 浏览器 E2E 覆盖暂停和继续

## 完成记录

- 后端新增 `PipelineStageState.confirmation_action`、`confirmation_feedback`、`confirmation_resolved_at` 字段和 `012_stage_confirmation_fields.py` 迁移。
- `complete_stage` 对 `confirmation_required=true` 的阶段进入 `waiting_confirmation`，普通 `start/complete` 不允许绕过等待态。
- `POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/confirm` 支持 `approve`、`revise`、`cancel`，并写入 `pipeline.confirm.*` 审计日志。
- StageRuntime 在等待确认时停止调用 SkillExecutionEngine；`revise` 后把用户反馈注入下一次同阶段执行的 `advanced_context.confirmation_feedback`。
- 前端 `ConfirmCard` 接入真实 PipelineRun / Artifact 状态，可确认继续、提交修改意见或终止需求。
- 浏览器 E2E `human-confirmation.spec.ts` 覆盖确认继续和提交修改意见。

## 不做

- 不做多人审批。
- 不做复杂审批流模板。
- 不做 GitHub PR review。
