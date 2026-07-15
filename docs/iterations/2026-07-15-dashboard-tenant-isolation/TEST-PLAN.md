# TASK-048 测试计划

## 红绿用例

1. Dashboard 双用户隔离
   - 当前用户和其他用户各创建不同状态、不同费用、不同时间的 Task。
   - 断言 tasks、today/yesterday/7d cost、recent_tasks 只包含当前用户。

2. Dashboard helper 契约
   - `_task_stats`、`_cost_stats`、`_recent_tasks` 必须传 `user_id`。
   - 状态计数和最近任务查询在 SQL 层过滤。

3. Cost API 双用户隔离
   - 断言 `/api/v1/cost` 已注册并可通过 Bearer Token 访问。
   - Task 总成本、总数和 TaskExecution model_costs 只统计当前用户。

4. 既有回归
   - Agent/Skill 全局统计不变。
   - Evaluation、Skill authorization 和 LLM usage 指标继续按用户隔离。

## 验证命令

```bash
uv run --extra dev pytest -q tests/api/test_dashboard.py tests/api/test_cost.py tests/api/test_route_prefixes.py
uv run --extra dev pytest -q
```

## 启动验证

```bash
PYTHONPATH=src JWT_SECRET_KEY=test-secret .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 18148
```

日志需到达 `Application startup complete`；sandbox 端口限制单独记录。
