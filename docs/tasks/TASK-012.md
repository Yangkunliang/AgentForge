# TASK-012：核心功能路线图与任务重排

**状态**：done
**优先级**：P0
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**关联架构**：[CORE-DEV-WORKFLOW.md](../architecture/CORE-DEV-WORKFLOW.md)

## 目标

把 AgentForge 的核心能力从零散框架能力收敛成连续的开发闭环，并拆出 TASK-013 至 TASK-019，避免完成 Project 底座后遗忘 Pipeline、Artifact、Bridge 和 Delivery。

## related_requirements

- CDW-01：Session 归属 Project
- CDW-02：主动授权代码库上下文
- CDW-03：需求类型生成阶段计划
- CDW-04：阶段输出成为 Artifact
- CDW-05：关键节点人工确认
- CDW-06：读取真实代码库
- CDW-07：结果回到项目

## deliverable

- `docs/architecture/CORE-DEV-WORKFLOW.md`
- `docs/iterations/2026-07-08-core-dev-workflow/`
- `docs/tasks/TASK-013.md` 至 `docs/tasks/TASK-019.md`
- 更新 `docs/tasks/CHECKLIST.md`、`docs/README.md`、`MEMORY.md`、`CLAUDE.md`

## acceptance

- [x] 定义核心闭环：Project -> Mount -> Session -> PipelineRun -> StageState -> Artifact -> Delivery
- [x] TASK-013 至 TASK-019 有独立任务文件和依赖关系
- [x] TASK-007 的静态原型边界与真实实现任务分离
- [x] 文档索引和项目记忆同步

## 不做

- 不实现数据库表、API、前端接入或 Bridge。
- 不修改业务代码。
- 不把后续任务提前标记完成。
