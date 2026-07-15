# TASK-046 迭代复盘

## 当前状态

代码、文档、后端全量测试、前端构建和 FastAPI 生命周期验证已完成。Dashboard 浏览器 E2E 已建立并可被 Playwright 正确发现，但 sandbox 禁止本地 Vite 测试服务器绑定端口，无沙箱执行申请也被策略拒绝；用户已批准继续推进后续任务，本轮将该限制作为环境豁免记录，不把 E2E 误报为通过。

## 完成内容

- 修复真实运行时契约错位：StageRuntime 使用 `evaluation_context`，SkillExecutionEngine 此前只读取测试使用的 `eval`，导致 TASK-045 在真实 Pipeline 中不写 LLM EvalEvent。
- StageRuntime 将非敏感 `stage_name` 注入 evaluation context，SkillExecutionEngine 写入 LLM 事件 metadata。
- Evaluation summary 新增仅基于 `llm_*` 的 `llm_by_model_route` 和 `llm_by_stage`，按成本、Token、调用次数稳定排序。
- Dashboard API 返回当前用户的 LLM 调用、Token、成本、平均延迟和前 3 成本排行。
- Dashboard 增加“LLM 实际用量”区域，旧费用卡明确为“任务费用（今日）”，并实现零数据和移动端布局。
- 新增 Dashboard Playwright E2E，覆盖总览、排行和两个独立空状态。

## 红绿证据

- Engine 规范上下文红灯：`NoResultFound`，证明 `evaluation_context` 未被消费；修复后通过。
- StageRuntime 名称透传红灯：evaluation context 缺少 `stage_name`；修复后通过。
- Evaluation 维度红灯：`KeyError: llm_by_model_route`；实现后通过。
- Dashboard API 红灯：`EvaluationStats` 缺少 `llm`；实现后通过。
- 前端 E2E 执行在进入页面断言前被环境阻断：Vite 绑定 `::1:3000` 返回 `EPERM`，不属于功能红灯。

## 验证结果

- Evaluation / Engine / Pipeline 相关回归：`19 passed, 13 warnings`。
- Dashboard / Evaluation API 回归：`15 passed, 9 warnings`。
- 后端全量：`341 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`npm run build` 通过；保留既有 Sass legacy / `@import`、Rollup pure annotation 和 chunk size 警告。
- Playwright 测试发现：`2 tests in 1 file`。
- Playwright 实际执行：未完成，sandbox 禁止本地端口绑定，无沙箱执行申请被拒绝。
- FastAPI：日志到达 `AgentForge startup complete` 和 `Application startup complete`；随后 sandbox 拒绝绑定 `127.0.0.1:18147`，应用正常关闭。
- 依赖审计：`npm install` 仍报告 `1 moderate + 1 high`，未执行破坏性 `npm audit fix --force`。

## 新发现风险

- Dashboard 的 Evaluation 指标已按当前用户隔离，但既有 Task 数量、任务费用和最近任务 helper 未接收 `user_id`。如果普通用户可访问 Dashboard，这可能形成跨用户任务描述和费用泄露，应作为下一项 P0 独立修复并补权限回归。
- 当前 Evaluation 聚合在请求时加载事件并在 Python 中聚合；数据量增长后需要按真实性能指标决定数据库聚合或物化视图，当前不提前优化。
- `stream_complete` usage 尚未采集，Dashboard 目前只代表已记录的非流式 tool-use 决策调用。

## 后续优先级

1. Dashboard 多租户数据隔离：Task stats、任务费用、最近任务按当前用户过滤。
2. `stream_complete` usage 稳定采集，补齐模型调用覆盖率。
3. `budget_policy` 接入 GovernancePolicy，实现超预算确认或拦截。
