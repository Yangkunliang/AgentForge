# 核心开发闭环迭代复盘

**日期**：2026-07-08
**任务**：TASK-012
**结论**：本迭代只完成路线图与任务拆分，不实现业务代码。

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
- Bridge 和写回能力放到后段，避免拖慢 Project/Artifact/Pipeline 底座。

## 后续提醒

- TASK-013 完成前，不要继续把 Project mock 当作真实项目管理。
- TASK-015 完成前，不要声称需求类型已经驱动真实流水线。
- TASK-016 完成前，不要声称阶段产物可复用。
- TASK-018 完成前，不要声称 Agent 已经能读取用户真实代码库。
