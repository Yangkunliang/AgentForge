# TASK-015：PipelineRun / StageState 阶段状态机

**状态**：done
**优先级**：P0
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-013

**依赖状态**：TASK-013 已完成，Session 已具备 `project_id`、`intent_type`、`current_pipeline_run_id` 字段，可继续接 PipelineRun / StageState。

## 目标

让需求类型 intent 生成真实的 PipelineRun 和 StageState，使阶段预览从 UI 装饰变成可持久化、可恢复、可推进的运行时状态。

## related_requirements

- CDW-03：需求类型生成阶段计划
- CDW-05：关键节点人工确认

## 技术子项

- [x] 新增 `PipelineRun` 模型和 migration
- [x] 新增 `PipelineStageState` 模型和 migration
- [x] 定义后端 pipeline 配置表，覆盖 new_feature / iteration / ui_adjust / bug_fix
- [x] `POST /sessions/{id}/chat` 首次发送时创建 PipelineRun
- [x] StagePreview 从后端 StageState 渲染
- [x] 支持 optional 阶段 skip / restore
- [x] 新增 `pipeline_started`、`stage_started`、`stage_completed`、`stage_skipped` SSE 事件
- [x] StageRuntime 负责调用现有 SkillExecutionEngine
- [x] 更新 `docs/tech-design/API-SPEC.md` 和 `docs/tech-design/SSE-EXECUTION-VISUALIZATION.md`

## acceptance

- [x] 选择不同 intent 后创建不同阶段列表
- [x] StageState 可持久化，刷新页面后阶段状态不丢
- [x] optional 阶段跳过后后端状态为 skipped
- [x] 当前阶段完成后可进入下一阶段
- [x] 后端状态机单测覆盖 pending/running/completed/skipped/failed
- [x] `uv run --extra dev pytest` 通过

## 不做

- 不做 Artifact Viewer。
- 不做人工确认 UI 的完整流转。
- 不做 Bridge 文件读取。
