# TASK-048 技术设计：Dashboard 多租户隔离

## 事实源

`Task.user_id` 是任务租户归属键。`created_by` 表示创建者，`assignee_id` 表示执行负责人，均不能替代任务所属用户边界。

## 查询契约

Dashboard helper 改为强制传入用户：

```python
_task_stats(db, *, user_id: str)
_count_by_status(db, status, *, user_id: str)
_cost_stats(db, *, user_id: str)
_sum_cost_on_date(db, date, *, user_id: str)
_recent_tasks(db, *, user_id: str, limit: int = 5)
```

每个 Task SQL 都必须在数据库查询阶段包含：

```python
Task.user_id == user_id
```

不得先查询全表再在 Python 响应层过滤。

## Dashboard 数据流

```text
get_current_user()
  -> current_user.id
  -> task stats / task cost / recent tasks
  -> EvaluationService.get_summary(user_id=current_user.id)
```

Agent 和 Skill 当前是平台级注册资源，不包含用户归属字段，继续返回全局数量。

## Cost API

`agent_forge.api.routes.cost` 保持兼容路径，注册到 FastAPI `/api/v1/cost`。端点使用 `current_user.id` 过滤：

- Task 总成本和数量：日期 + `Task.user_id`。
- 模型成本：`TaskExecution JOIN Task` 后增加日期 + `Task.user_id`。

## 安全约束

- `user_id=None` 的历史 Task 不展示给任何普通用户。
- 不允许 helper 的 `user_id` 使用可选默认值。
- HTTP 测试必须使用当前用户 Token，不能只调用内部函数证明隔离。
- 查询结果不返回其他用户任务 ID、描述、状态或费用。

## 兼容性

- Dashboard 响应结构不变。
- Cost API 响应结构不变。
- 不修改前端类型和组件。
