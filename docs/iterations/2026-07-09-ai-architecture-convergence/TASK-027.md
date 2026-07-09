# TASK-027: AI Runtime Baseline 与契约文档

```yaml
id: AIARCH-P0-001
module: architecture
priority: P0
title: AI Runtime Baseline 与契约文档
related_requirements:
  - R-001
  - R-008
deliverable:
  - docs/architecture/AI-RUNTIME-CONVERGENCE.md
  - docs/iterations/2026-07-09-ai-architecture-convergence/*
acceptance:
  - 明确 Project -> Intent -> Pipeline -> Stage -> Agent/Profile -> Skill Runtime -> Artifact -> Delivery -> Eval Feedback 主链路
  - 明确当前代码模块和目标运行时契约的映射关系
  - 明确后续 TASK-028 到 TASK-034 的依赖关系
status: done
```

## 背景

这是后续所有代码任务的基准任务。先把“AI 架构收敛”从口头方向变成可维护的架构文档和任务契约，避免后续实现时每个模块各自理解。

## 范围

- 盘点当前真实运行路径。
- 定义 AI Runtime Contract。
- 明确核心领域对象和边界。
- 明确哪些现有文档需要在后续任务中更新。

## 实施 checklist

- 阅读 `src/agent_forge/pipeline/`、`src/agent_forge/skills/`、`src/agent_forge/llm/`、`src/agent_forge/agents/`。
- 阅读 `docs/architecture/CORE-DEV-WORKFLOW.md`、`docs/architecture/AGENT-MODEL.md`、相关 `tech-design` 文档。
- 新增 `docs/architecture/AI-RUNTIME-CONVERGENCE.md`。
- 在文档中列出当前路径、目标路径、差距、迁移原则。
- 更新 `docs/README.md` 架构文档索引。

## 验收标准

- 后续任务能直接引用该文档中的对象名和数据流。
- 文档没有把开发 AgentForge 的视角和平台用户视角混淆。
- 明确说明本次收敛不是推倒重写，而是复用现有 Project / Pipeline / Skill / Delivery 基础。

## 验证

```bash
git diff --check
```

```bash
rg -n "AI-RUNTIME-CONVERGENCE|Project -> Intent|AgentProfile|ModelRoute|SkillRuntime" docs
```
