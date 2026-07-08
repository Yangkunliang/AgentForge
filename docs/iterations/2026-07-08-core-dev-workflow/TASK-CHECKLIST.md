# 核心开发闭环任务清单

**日期**：2026-07-08
**Epic**：EPIC-CORE-DEV-WORKFLOW

## 用户故事覆盖矩阵

| 用户故事 | 覆盖任务 |
|----------|----------|
| CDW-01：Session 归属 Project | TASK-013、TASK-014 |
| CDW-02：主动授权代码库上下文 | TASK-013、TASK-018 |
| CDW-03：需求类型生成阶段计划 | TASK-015 |
| CDW-04：阶段输出成为 Artifact | TASK-013、TASK-016 |
| CDW-05：关键节点人工确认 | TASK-017 |
| CDW-06：读取真实代码库 | TASK-018 |
| CDW-07：结果回到项目 | TASK-019 |

## 任务索引

| 状态 | 任务 | 优先级 | 目标 | 依赖 |
|------|------|--------|------|------|
| done | TASK-012：核心功能路线图与任务重排 | P0 | 明确核心闭环、修正状态漂移、拆出后续任务 | 无 |
| todo | TASK-013：Project / Mount / Artifact 数据底座 | P0 | 建立核心实体、API 和 Session.project_id | TASK-012 |
| todo | TASK-014：项目管理页接真实数据 | P0 | 去掉项目 mock，ProjectBar 和 Projects 页接 API | TASK-013 |
| todo | TASK-015：PipelineRun / StageState 阶段状态机 | P0 | intent 生成真实阶段计划和状态流转 | TASK-013 |
| todo | TASK-016：Artifact 产物归档与查看 | P1 | 阶段输出保存、查看、作为上下文复用 | TASK-015 |
| todo | TASK-017：人工确认与阶段继续机制 | P1 | PRD/技术选型/影响范围暂停确认后继续 | TASK-015、TASK-016 |
| todo | TASK-018：Agent Bridge / 真实代码库读取 | P1 | 本地 mount、连接状态、授权文件读取 | TASK-013、TASK-017 |
| todo | TASK-019：写回与交付闭环 | P2 | 生成 diff、写回本地、导出交付结果 | TASK-016、TASK-018 |

## 依赖图

```text
TASK-012
  -> TASK-013
    -> TASK-014
    -> TASK-015
      -> TASK-016
      -> TASK-017
        -> TASK-018
          -> TASK-019
```

## 防遗忘机制

- `docs/tasks/CHECKLIST.md` 必须保留 TASK-013 至 TASK-019 的 todo 状态。
- 每个任务有独立 `docs/tasks/TASK-NNN.md`，不得只存在于本迭代目录。
- 每完成一个任务，只能标记该任务 done，不得顺手标记后续任务。
- TASK-013 完成后必须更新 TASK-014 和 TASK-015 的依赖状态说明。
- TASK-015 完成后必须检查 TASK-016 和 TASK-017 是否仍在任务索引中。
