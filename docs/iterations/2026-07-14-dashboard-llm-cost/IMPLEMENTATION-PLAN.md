# Dashboard LLM 成本与用量 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 TASK-045 已采集的 LLM usage 以当前用户隔离的方式接入 Dashboard，并展示总览与 ModelRoute / Stage 排行。

**Architecture:** `EvaluationService` 负责从 `llm_*` EvalEvent 生成完整维度聚合，Dashboard 路由只负责收敛成有界的前 3 排行，Vue 页面只消费 API 契约。Stage 名称通过非敏感 evaluation context 进入 LLM 事件 metadata，历史数据缺失名称时回退 stage id。

**Tech Stack:** Python 3.14、FastAPI、SQLAlchemy async、pytest、Vue 3、TypeScript、Element Plus、Playwright。

## Global Constraints

- 不新增数据库表或外部依赖。
- Dashboard LLM 数据必须按当前登录用户过滤。
- 只统计 `event_type.startswith("llm_")` 的事件。
- 不记录或返回 prompt、用户消息、源码正文、工具输出或凭据。
- 不采集 `stream_complete` usage，不实现预算拦截。
- 前端保持现有 Vue 3、Element Plus 和 Dashboard 视觉体系。

---

### Task 1: Evaluation LLM 维度聚合

**Files:**
- Modify: `tests/api/test_evaluation.py`
- Modify: `tests/skills/test_engine_context.py`
- Modify: `src/agent_forge/evaluation/service.py`
- Modify: `src/agent_forge/pipeline/runtime.py`
- Modify: `src/agent_forge/skills/engine.py`

**Interfaces:**
- Consumes: `EvaluationService.get_summary(db, user_id=...) -> dict[str, Any]`、`advanced_context["evaluation_context"]`。
- Produces: `summary["llm_by_model_route"]`、`summary["llm_by_stage"]`，以及 `llm_tool_use_completed.metadata.stage_name`。

- [x] **Step 1: 写 Evaluation 聚合红灯测试**

  新增测试数据，包含两个 route、两个 stage、一个非 LLM 事件；断言 `llm_by_model_route` 和 `llm_by_stage` 只统计 LLM 事件，并按成本降序。

- [x] **Step 2: 运行红灯测试**

  Run: `uv run --extra dev pytest -q tests/api/test_evaluation.py -k llm_usage_dimensions`

  Expected: FAIL，原因是 summary 尚无 `llm_by_model_route` 或 `llm_by_stage`。

- [x] **Step 3: 实现最小聚合**

  在 `EvaluationService.get_summary()` 中先提取 `llm_events`，复用 `_metric_block(llm_events)`，新增 `_group_llm_by_model_route()` 和 `_group_llm_by_stage()`；每行输出 `total_calls/tokens_used/cost_usd/average_latency_ms`。

- [x] **Step 4: 补充 stage name 事件测试和实现**

  扩展 SkillExecutionEngine 测试，给 evaluation context 注入 `stage_name` 并断言 metadata；StageRuntime 构造 context 时加入 `stage_name`，Engine 只复制非空字符串。

- [x] **Step 5: 运行聚合和运行时相关测试**

  Run: `uv run --extra dev pytest -q tests/api/test_evaluation.py tests/skills/test_engine_context.py tests/pipeline/test_runtime.py`

  Expected: PASS。

### Task 2: Dashboard API 契约

**Files:**
- Modify: `tests/api/test_dashboard.py`
- Modify: `src/api/routes/dashboard.py`

**Interfaces:**
- Consumes: `summary["llm"]`、`summary["llm_by_model_route"]`、`summary["llm_by_stage"]`。
- Produces: `DashboardResponse.evaluation.llm: LLMUsageStats`。

- [x] **Step 1: 写 Dashboard API 红灯测试**

  在当前用户项目下写入四个以上 LLM 事件，断言 `_get_evaluation_stats(db, user_id=...)` 返回总览和成本最高的前 3 route/stage。

- [x] **Step 2: 运行红灯测试**

  Run: `uv run --extra dev pytest -q tests/api/test_dashboard.py -k llm_usage`

  Expected: FAIL，原因是 `EvaluationStats` 尚无 `llm`。

- [x] **Step 3: 实现 Pydantic schema 与映射**

  新增 `LLMUsageDimension`、`LLMModelRouteUsage`、`LLMStageUsage`、`LLMUsageStats`，在 `_get_evaluation_stats()` 中映射 summary，并对排行切片 `[:3]`。

- [x] **Step 4: 运行 Dashboard 回归**

  Run: `uv run --extra dev pytest -q tests/api/test_dashboard.py tests/api/test_evaluation.py`

  Expected: PASS。

### Task 3: Dashboard Vue 面板

**Files:**
- Create: `web/e2e/dashboard.spec.ts`
- Modify: `web/src/types/index.ts`
- Modify: `web/src/views/dashboard/Index.vue`

**Interfaces:**
- Consumes: `DashboardStats.evaluation.llm`。
- Produces: “LLM 实际用量”总览、ModelRoute 排行、Stage 排行和零数据状态。

- [x] **Step 1: 写浏览器红灯测试**

  Mock `/api/v1/dashboard`，分别返回完整 LLM 指标和空指标；断言页面标题、四项数值、排行、两个空状态及“任务费用（今日）”。

- [ ] **Step 2: 运行浏览器红灯测试（环境阻塞）**

  Run: `cd web && npx playwright test e2e/dashboard.spec.ts`

  Expected: FAIL，原因是页面尚无“LLM 实际用量”。

  实际：Playwright 能发现测试，但 sandbox 禁止 Vite 绑定本地端口，测试未进入页面断言。

- [x] **Step 3: 实现类型和页面**

  在 `web/src/types/index.ts` 增加 LLM usage 类型；在 Dashboard 使用 0 值 fallback、数字格式化函数、四列稳定指标网格和两列排行，窄屏分别降为两列和单列。

- [x] **Step 4: 运行前端构建**

  Run: `cd web && npm run build`

  Expected: `vue-tsc` 和 `vite build` 均成功。

- [ ] **Step 5: 运行浏览器 E2E（环境阻塞）**

  Run: `cd web && npx playwright test e2e/dashboard.spec.ts`

  Expected: PASS。当前 sandbox 禁止 Vite 绑定本地端口，已在迭代复盘中记录环境豁免，不视为测试通过。

### Task 4: 文档、完整验证与集成

**Files:**
- Modify: `docs/iterations/2026-07-14-dashboard-llm-cost/TASK-CHECKLIST.md`
- Create: `docs/iterations/2026-07-14-dashboard-llm-cost/ITERATION-REVIEW.md`
- Modify: `docs/README.md`
- Modify: `docs/tech-design/API-SPEC.md`
- Modify: `docs/architecture/AI-RUNTIME-CONVERGENCE.md`
- Modify: `MEMORY.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: 已验证的 API 与页面行为。
- Produces: TASK-046 当前事实、验证证据和后续任务边界。

- [x] **Step 1: 同步文档和 checklist**

  更新 API 示例、AI Runtime 当前状态、索引、根上下文和迭代复盘；所有完成项改为 `[x]`。

- [x] **Step 2: 执行后端全量测试和前端构建**

  Run: `uv run --extra dev pytest -q`

  Expected: 基线测试全部通过，允许仓库既有 skip/xfail/warning。

  Run: `cd web && npm run build`

  Expected: 构建成功，允许仓库既有 Sass 和 chunk size 警告。

- [x] **Step 3: 验证 FastAPI 生命周期并恢复测试数据库**

  Run: `PYTHONPATH=src JWT_SECRET_KEY=test-secret .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 18147`

  Expected: 日志到达 `Application startup complete`；随后停止进程。复制主工作区干净的 `test_db.sqlite` 回工作树。

- [ ] **Step 4: 提交、推送和合并**

  使用中文功能提交信息推送 `feature/task-046-dashboard-llm-cost`；在主工作区 fast-forward 合并，复验后推送 `main`。
