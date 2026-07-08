# TASK-015：PipelineRun / StageState 阶段状态机

**状态**：todo
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

- [ ] 新增 `PipelineRun` 模型和 migration
- [ ] 新增 `PipelineStageState` 模型和 migration
- [ ] 定义后端 pipeline 配置表，覆盖 new_feature / iteration / ui_adjust / bug_fix
- [ ] `POST /sessions/{id}/chat` 首次发送时创建 PipelineRun
- [ ] StagePreview 从后端 StageState 渲染
- [ ] 支持 optional 阶段 skip / restore
- [ ] 新增 `pipeline_started`、`stage_started`、`stage_completed`、`stage_skipped` SSE 事件
- [ ] StageRuntime 负责调用现有 SkillExecutionEngine
- [ ] 更新 `docs/tech-design/API-SPEC.md` 和 `docs/tech-design/SSE-EXECUTION-VISUALIZATION.md`

## acceptance

- [ ] 选择不同 intent 后创建不同阶段列表
- [ ] StageState 可持久化，刷新页面后阶段状态不丢
- [ ] optional 阶段跳过后后端状态为 skipped
- [ ] 当前阶段完成后可进入下一阶段
- [ ] 后端状态机单测覆盖 pending/running/completed/skipped/failed
- [ ] `uv run --extra dev pytest` 通过

## 不做

- 不做 Artifact Viewer。
- 不做人工确认 UI 的完整流转。
- 不做 Bridge 文件读取。
