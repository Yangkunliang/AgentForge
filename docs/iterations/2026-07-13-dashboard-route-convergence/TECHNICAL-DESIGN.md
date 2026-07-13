# TASK-043 技术设计

## 当前问题

- `src/api/routes/dashboard.py` 是 `api.main` 挂载的真实路由。
- `src/agent_forge/api/routes/dashboard.py` 保留了另一份旧实现。
- `tests/api/test_dashboard.py` 主要导入旧模块，因此可能出现测试通过但真实路由 schema 漂移。

## 方案

1. 将测试导入改为 `api.routes.dashboard`。
2. 旧 `agent_forge.api.routes.dashboard` 改为从真实模块 re-export 公共对象。
3. 文档记录 Dashboard 单一事实源，后续新增字段只修改真实模块。

## 伴随修正

测试切换到真实模块后暴露出 `src/api/routes/dashboard.py` 的 `_agent_stats()` 将所有 Agent 都计入 active，inactive 固定返回 0。本任务同步修正为按 `Agent.status == "active" / "inactive"` 分别计数。

## 风险控制

- 不删除旧模块文件，避免外部兼容 import 直接断裂。
- 不修改路由前缀和鉴权依赖。
- 使用 Dashboard/Evaluation 相关测试确认行为不变。
