# TASK-034: 架构文档收敛与迁移清理

```yaml
id: AIARCH-P2-008
module: docs
priority: P2
title: 架构文档收敛与迁移清理
related_requirements:
  - R-008
deliverable:
  - docs/architecture/*
  - docs/tech-design/*
  - docs/README.md
  - MEMORY.md
  - CLAUDE.md
acceptance:
  - 架构文档描述和真实代码路径一致
  - 旧 Harness、LLM、Skill、Pipeline 设计文档标明当前状态或迁移结论
  - 新人可以通过 docs/README.md 找到最新 AI Runtime 主线
status: todo
```

## 背景

架构文档如果持续落后，会让后续 Agent 和人都重复踩坑。本任务在代码任务完成后统一收敛文档，避免蓝图和真实实现分叉。

## 范围

- 更新 `docs/architecture/`。
- 更新相关 `docs/tech-design/`。
- 更新 `docs/README.md`。
- 如架构概要变化，更新仓库根目录 `MEMORY.md` 和 `CLAUDE.md`。
- 标注历史文档和当前实现差异。

## 实施 checklist

- 逐项检查 TASK-028 到 TASK-033 的代码变更和接口。
- 更新 AI Runtime 主线文档。
- 更新 Agent 模型文档。
- 更新 LLM 配置文档。
- 更新 Skill 引擎文档。
- 更新 API-SPEC。
- 更新 DATABASE。
- 更新 SECURITY 中 Skill 和 Credential 相关策略。
- 更新 docs/README 索引。
- 新增 ITERATION-REVIEW.md。

## 验收标准

- `docs/README.md` 能导航到最新架构主线。
- 文档中不再把“计划中能力”写成“已实现能力”。
- 历史文档保留可追溯，但明确当前推荐阅读路径。
- 迭代 review 写清完成情况、遗留风险和下一步建议。

## 验证

```bash
git diff --check
```

```bash
rg -n "AI Runtime|ModelRoute|AgentProfile|SkillRuntime|EvalFeedback" docs MEMORY.md CLAUDE.md
```
