# TASK-048 迭代复盘：Dashboard 多租户隔离

## 完成内容

- Dashboard `tasks`、`cost`、`recent_tasks` 的所有 Task SQL 强制传入并过滤 `user_id`。
- 无归属 Task 不对任何普通用户展示，不计入任务和费用统计。
- `/api/v1/cost` 恢复主 FastAPI 路由挂载。
- Cost API 的 Task 总成本、数量和 `TaskExecution JOIN Task` 模型费用均按当前用户过滤。
- Dashboard 与 Cost 统一使用支持 Bearer/API Key 的认证依赖；停用 API Key 不再通过认证。
- Agent/Skill 数量保留平台级统计语义，Evaluation 保留 Project -> user_id 隔离语义。

## TDD 与评审

红灯证据：

- Dashboard helper 不接受 `user_id`，双用户数据被合并为全局统计。
- 文档声明的 `/api/v1/cost` 实际返回 404。
- 停用 API Key 仍可访问 Dashboard。
- 首版 Cost 测试污染共享 `fake_user`，导致后续任务列表序列化失败；改用测试专属用户和真实认证链后消除污染。

独立评审首次发现“停用 API Key 未过滤”和“测试覆盖绕过真实认证”两个 Important；修正后复审 Critical 0、Important 0，可合并。

## 验证证据

- Dashboard + Cost + 路由定向：`13 passed`。
- 真实认证与原认证回归：`9 passed`。
- 后端全量：`354 passed, 6 skipped, 11 xfailed, 41 warnings`。
- Ruff：本次生产文件和测试 `E/F/I` 通过；`src/api/main.py` 保留仓库既有 `.env` 预加载结构，使用忽略既有 E402/E501 的 E/F 校验并通过。
- FastAPI：到达 `AgentForge startup complete` 和 `Application startup complete`；sandbox 禁止绑定 `127.0.0.1:18148` 后正常 shutdown。

## 残余风险

- `APIKey.last_used_at` 当前不是数据库映射字段，使用时间不会持久化，不能作为审计事实；需要后续模型和迁移任务。
- API Key 自身的 permission scope 尚未贯穿路由授权，当前仍主要依赖所属 User permissions；这是独立的授权模型增强，不在本次租户隔离范围。
- Task `user_id=None` 历史记录被严格排除；如需归属修复，应通过单独数据治理任务显式迁移，不能自动猜测所属用户。
