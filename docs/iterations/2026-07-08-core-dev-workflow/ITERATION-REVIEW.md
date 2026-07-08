# 核心开发闭环迭代复盘

**日期**：2026-07-08
**任务**：TASK-012
**结论**：本迭代只完成路线图与任务拆分，不实现业务代码。

> 2026-07-08 状态更新：TASK-013、TASK-014、TASK-015、TASK-016、TASK-017、TASK-018、TASK-019 已完成；Project 真实数据流、PipelineRun / StageState 状态机、Artifact 归档查看与上下文复用、人工确认与阶段继续、Bridge 授权文件读取、Delivery diff 预览与确认写回已可用。

## 完成内容

- 新增 `docs/architecture/CORE-DEV-WORKFLOW.md`，定义 Project、Mount、Session、PipelineRun、StageState、Artifact、Delivery 的产品和技术边界。
- 新增核心闭环迭代目录，沉淀产品需求、任务清单、技术设计和测试计划。
- 新增 TASK-012 至 TASK-019 的任务文件，避免后续阶段在 TASK-013 完成后被遗忘。
- 更新全局任务索引、文档索引、CLAUDE.md 和 MEMORY.md。
- 将 TASK-007 定位为静态原型任务，真实能力拆入 TASK-013 至 TASK-019。

## 关键决策

- 不把核心闭环做成一个巨型任务。
- TASK-013 先做数据底座，不抢跑 Bridge。
- intent 必须在 TASK-015 后成为 PipelineRun，而不是只写入 prompt。
- Artifact 必须成为独立实体，不能只存在于聊天消息。
- Bridge 和写回能力放到后段，避免拖慢 Project/Artifact/Pipeline 底座；TASK-018/TASK-019 已按该顺序落地。

## 后续提醒

- TASK-013、TASK-014 已完成，Project mock 已被真实项目数据流替换。
- TASK-015 已完成，需求类型已经生成可持久化 PipelineRun / StageState。
- TASK-016 已完成，阶段输出已成为可查看、可复用、可作为上下文引用的 Artifact；但完整开发闭环仍依赖确认机制、Bridge 和 Delivery。
- TASK-017 已完成，关键阶段可以进入 `waiting_confirmation`，用户确认后继续、提出修改意见后回到同阶段重新执行、取消后终止 run。
- TASK-018 已完成，Agent 可读取用户在 connected local Mount 中选中的授权文件。
- TASK-019 已完成，Artifact Viewer 可生成 diff、确认写回 connected local Mount、写前备份、保存 Delivery report 并导出 Markdown；GitHub PR 和 zip 交付仍是后续增强。
