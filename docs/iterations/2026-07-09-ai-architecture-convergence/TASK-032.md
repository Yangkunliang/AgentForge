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
status: done
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

- [x] 梳理现有 Pipeline confirmation 字段和 API。
- [x] 梳理 `src/agent_forge/harness/` 中治理相关能力。
- [x] 设计统一 GovernanceDecision：allow、require_confirmation、deny。
- [x] Pipeline 创建阶段状态时根据 StageDefinition.confirmation_policy 写入 GovernancePolicy 结果。
- [x] SkillDispatcher 调用高风险 Skill 前调用 GovernancePolicy。
- [x] Delivery 本地写回、GitHub PR、zip 包确认前复用 GovernancePolicy。
- [x] 前端 ConfirmCard 展示 policy reason 和 impact scope。
- [x] 审计日志写入 `governance_decision` 上下文。

## 实现结果

- 新增 `src/agent_forge/governance/policy.py`，统一输出 `GovernanceDecision` 和 `GovernancePolicy`。
- `PipelineStageState` 新增 `confirmation_type`、`confirmation_reason`、`confirmation_impact_scope`、`confirmation_audit_payload`，并通过迁移 `018_governance_confirmation_context.py` 落库。
- `PipelineService` 创建 PipelineRun 时根据阶段确认策略固化治理决策，`pipeline.confirm.*` 审计日志回写对应决策上下文。
- Delivery 本地写回、GitHub PR、zip Package 在未显式确认时统一记录 `missing_confirmation` 类型的治理决策。
- `SkillPermissionPolicy` 对高风险权限走 `GovernancePolicy.evaluate_skill_call()`，拒绝审计中包含权限、风险等级和影响范围。
- `ConfirmCard` 渲染确认原因与影响范围，让用户确认前能看到策略判断依据。

## 验收标准

- PRD / 需求 Diff 阶段默认可要求确认。
- 引入新中间件或大范围改动时能要求技术选型确认。
- 写回本地目录或创建 PR 前能展示影响范围。
- 高风险 Skill 调用不能绕过策略。
- 所有确认动作写入审计日志。

## 验证

```bash
uv run --extra dev pytest tests/harness/test_governance.py tests/api/test_pipeline_runs.py tests/api/test_delivery.py tests/skills/test_dispatcher.py
```

```bash
npm run build
```

前端命令在 `/Users/yangkl/AgentForge/web` 下执行。
