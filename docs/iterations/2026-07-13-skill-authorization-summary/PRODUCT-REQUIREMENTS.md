# TASK-041 产品需求：高风险 Skill 授权聚合指标

## 背景

TASK-040 已经把高风险 Skill 授权请求和授权使用写入 EvalEvent。仅有原始事件还不够，后续 Dashboard、策略优化和导出分析需要稳定的聚合字段。

## 目标

- 在 Evaluation summary 中新增 `skill_authorizations` 聚合块。
- 支持查看授权请求数、授权使用数、授权率。
- 支持按 Skill 和权限维度聚合。

## 非目标

- 不新增前端 Dashboard 视图。
- 不改变 EvalEvent 表结构。
- 不改变授权策略本身。

## 验收标准

- `/api/v1/evaluation/summary` 返回 `skill_authorizations`。
- 聚合只消费 `skill_authorization_required` 和 `skill_authorization_granted` 事件。
- 空数据时返回稳定的 0 值和空列表。
