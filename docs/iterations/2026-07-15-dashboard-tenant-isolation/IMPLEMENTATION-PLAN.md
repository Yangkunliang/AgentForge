# TASK-048 实施计划：Dashboard 多租户隔离

## Task 1：设计与边界

- [x] 明确 `Task.user_id` 为租户事实源。
- [x] 明确 Dashboard 私有统计与 Agent/Skill 平台统计边界。
- [x] 把未挂载 `/api/v1/cost` 纳入同一费用隔离修复。

Commit: `feat-设计Dashboard多租户隔离迭代`

## Task 2：Dashboard 红灯与实现

Files:

- Modify: `tests/api/test_dashboard.py`
- Modify: `src/api/routes/dashboard.py`

步骤：

- [ ] 建立两个用户及各自 Task 数据。
- [ ] 断言 tasks、cost、recent_tasks 只返回当前用户。
- [ ] 观察现有 helper 不接收 `user_id` 或返回跨用户数据的红灯。
- [ ] 在每条 Task SQL 中加入 `Task.user_id == user_id`。
- [ ] 运行 Dashboard 定向测试并提交。

Commit: `fix-隔离Dashboard用户任务数据`

## Task 3：Cost API 红灯与实现

Files:

- Modify: `tests/api/test_cost.py`
- Modify: `src/agent_forge/api/routes/cost.py`
- Modify: `src/api/main.py`

步骤：

- [ ] 用路由测试证明 `/api/v1/cost` 未注册。
- [ ] 用双用户 Task / TaskExecution 证明费用跨租户聚合。
- [ ] 挂载 Cost router，并用当前用户过滤三类查询。
- [ ] 运行 Cost 与路由回归并提交。

Commit: `fix-恢复并隔离用户费用接口`

## Task 4：验证、文档和集成

- [ ] 执行 Dashboard、Cost、路由定向测试。
- [ ] 执行后端全量测试和生产代码 lint。
- [ ] 验证 FastAPI 生命周期。
- [ ] 创建 `ITERATION-REVIEW.md` 并同步架构、API、README、MEMORY、CLAUDE。
- [ ] 独立代码评审无阻断问题。
- [ ] 推送功能分支，合并并推送 `main`。

Commit: `feat-完成Dashboard多租户隔离迭代`
