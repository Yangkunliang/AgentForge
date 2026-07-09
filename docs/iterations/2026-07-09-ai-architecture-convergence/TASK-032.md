# TASK-032: Governance 与人工确认策略引擎

```yaml
id: AIARCH-P1-006
module: governance
priority: P1
title: Governance 与人工确认策略引擎
related_requirements:
  - R-006
deliverable:
  - GovernancePolicy service
  - Pipeline confirmation policy integration
  - Skill high-risk confirmation
  - Audit integration
acceptance:
  - PRD、技术选型、影响范围、写回和高风险 Skill 调用能走统一确认策略
  - ConfirmCard 渲染策略结果
  - 审计日志记录确认上下文
status: todo
```

## 背景

AgentForge 的核心安全感来自“知道 AI 什么时候该停下来等人”。确认逻辑如果散落在各阶段，会难以维护，也容易漏掉高风险动作。

## 范围

- 定义 GovernancePolicy。
- 接入 StageDefinition.confirmation_policy。
- 接入 SkillPolicy 高风险动作。
- 接入 Delivery 写回确认。
- 确认结果写审计。

## 实施 checklist

- 梳理现有 Pipeline confirmation 字段和 API。
- 梳理 `src/agent_forge/harness/` 中治理相关能力。
- 设计统一 PolicyDecision：allow、require_confirmation、deny。
- StageRuntime 在阶段开始前和阶段完成后调用 GovernancePolicy。
- SkillDispatcher 调用高风险 Skill 前调用 GovernancePolicy。
- DeliveryService 写回前复用 GovernancePolicy。
- 前端 ConfirmCard 展示 policy reason 和 impact scope。

## 验收标准

- PRD / 需求 Diff 阶段默认可要求确认。
- 引入新中间件或大范围改动时能要求技术选型确认。
- 写回本地目录或创建 PR 前能展示影响范围。
- 高风险 Skill 调用不能绕过策略。
- 所有确认动作写入审计日志。

## 验证

```bash
uv run --extra dev pytest tests/harness/test_governance.py tests/api/test_pipeline_runs.py tests/api/test_delivery.py
```

```bash
npm run build
```

前端命令在 `/Users/yangkl/AgentForge/web` 下执行。
