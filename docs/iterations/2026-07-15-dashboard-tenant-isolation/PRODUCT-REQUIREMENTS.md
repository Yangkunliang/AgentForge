# TASK-048 产品需求：Dashboard 多租户隔离

## 背景

Dashboard 的 Evaluation 指标已按当前用户 Project 隔离，但任务数量、任务费用和最近任务直接聚合全表。多用户部署时，一个用户会看到其他用户的任务规模、描述、状态和成本。文档声明的 `/api/v1/cost` 也未挂载，且内部查询同样缺少用户过滤。

## 用户目标

登录用户只能看到归属于自己的任务统计、成本趋势、最近任务和按模型拆分的任务费用，不得通过 Dashboard 或费用 API 推断其他账号的数据。

## 范围

- Dashboard `tasks` 按 `Task.user_id` 隔离。
- Dashboard `cost` 按 `Task.user_id` 隔离。
- Dashboard `recent_tasks` 按 `Task.user_id` 隔离。
- `/api/v1/cost` 恢复路由挂载，并按当前用户隔离任务与 TaskExecution 成本。
- Evaluation 继续使用现有 Project -> user_id 隔离。
- Agent 和 Skill 数量继续表示平台级可用资源，不改为用户私有统计。

## 非目标

- 不改变 LLM EvalEvent 聚合语义。
- 不新增 Task 字段或数据库迁移。
- 不引入管理员跨租户 Dashboard。
- 不修改前端布局和展示口径。

## 验收标准

1. 双用户数据同时存在时，Dashboard 只返回当前用户任务。
2. 今日费用、昨日趋势、7 日费用和最近任务均不包含其他用户数据。
3. `/api/v1/cost` 可访问，并只聚合当前用户 Task 与 TaskExecution。
4. 所有 Task 聚合 helper 必须显式接收 `user_id`，避免调用方遗漏租户条件。
