# TASK-042 技术设计

## 数据来源

继续以 `EvaluationService.get_summary()` 为唯一聚合来源。TASK-041 已输出：

- `skill_authorizations.required`
- `skill_authorizations.granted`
- `skill_authorizations.grant_rate`
- `skill_authorizations.by_skill`
- `skill_authorizations.by_permission`

## 后端改动

`src/api/routes/dashboard.py` 的 `EvaluationStats` 增加 `skill_authorizations` 字段，直接映射 summary 中的授权聚合块。为避免旧模块和测试模块分叉，`src/agent_forge/api/routes/dashboard.py` 同步 schema。

## 前端改动

`web/src/types/index.ts` 增加授权指标类型；`web/src/views/dashboard/Index.vue` 继续使用 `dashboardApi.get()`，在现有 Agent & Skill 卡片下方增加一行授权指标区域。

## 边界处理

- 缺失 `skill_authorizations` 时前端兜底为 0 值，兼容旧后端。
- `grant_rate` 按百分比展示，后端仍保留 0～1 的数字契约。
- 排行只显示前 3 项，避免 Dashboard 被长列表撑开。

## 风险

- 当前存在两份 Dashboard 路由模块，容易出现 schema 漂移。本任务只做同步，后续应考虑删除或收敛旧 `agent_forge.api.routes.dashboard` 模块。
