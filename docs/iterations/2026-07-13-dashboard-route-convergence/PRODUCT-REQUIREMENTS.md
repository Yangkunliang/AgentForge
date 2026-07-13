# TASK-043 产品需求：Dashboard 路由单一事实源

## 背景

TASK-042 发现 Dashboard 有两份路由实现：真实应用挂载 `src/api/routes/dashboard.py`，测试和兼容导入仍引用 `src/agent_forge/api/routes/dashboard.py`。这种双实现会让后续 Dashboard schema、鉴权和聚合逻辑再次漂移。

## 目标

- Dashboard 运行时逻辑只保留一份事实源。
- 旧 import 路径继续可用，但不再包含第二份业务实现。
- 测试直接覆盖真实应用路由模块。

## 非目标

- 不收敛其他 legacy API 模块。
- 不改 Dashboard API 契约。
- 不改前端页面。

## 验收标准

- `tests/api/test_dashboard.py` 从真实 `api.routes.dashboard` 导入 helper。
- `src/agent_forge/api/routes/dashboard.py` 只做兼容 re-export。
- Dashboard 相关测试、Evaluation 测试、全量后端、前端构建和 FastAPI 启动均通过。
