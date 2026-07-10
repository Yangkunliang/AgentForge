# AI Runtime 收敛迭代复盘

```yaml
iteration: 2026-07-09-ai-architecture-convergence
scope: TASK-027..TASK-034
status: completed
completed_at: 2026-07-10
```

## 1. 完成范围

本轮迭代把 AgentForge 的 AI 架构从“分散功能集合”收敛成一条可持续演进的运行时主线：

```text
Project -> Intent -> Pipeline -> Stage -> Agent/Profile -> Skill Runtime -> Artifact -> Delivery -> Eval Feedback
```

已完成：

- TASK-027：建立 AI Runtime Contract 和迁移任务边界。
- TASK-028：Pipeline Catalog 成为阶段定义的后端唯一事实源。
- TASK-029：Agent 管理态配置通过 AgentResolver 进入 StageRuntime。
- TASK-030：Provider / Model / Credential / Route 分层，并由 ModelRouter 进入运行时。
- TASK-031：第三方 Skill 导入形成 Manifest、权限、安装、注册、调用和审计闭环。
- TASK-032：GovernancePolicy 统一阶段确认、交付确认和高风险 Skill 决策。
- TASK-033：EvalEvent 记录阶段、Skill、确认、交付和失败事实，并接入 Dashboard、Evaluation API 和 JSONL 导出。
- TASK-034：收敛架构、技术设计、索引和根上下文文档，明确当前推荐阅读路径。

## 2. 当前推荐阅读路径

新人或后续 Agent 需要理解当前系统时，优先按以下顺序阅读：

1. `docs/README.md`
2. `docs/architecture/AI-RUNTIME-CONVERGENCE.md`
3. `docs/architecture/CORE-DEV-WORKFLOW.md`
4. `docs/tech-design/ARCHITECTURE.md`
5. `docs/iterations/2026-07-09-ai-architecture-convergence/TASK-CHECKLIST.md`

其中 `AI-RUNTIME-CONVERGENCE.md` 是当前 AI Runtime 主线入口；`ARCHITECTURE.md` 保留 Harness 六层框架说明，但不再作为产品运行时主链路的唯一入口。

## 3. 验证记录

TASK-033 代码任务完成时已通过：

```bash
uv run --extra dev pytest -q
```

结果：`324 passed, 6 skipped, 11 xfailed`。

```bash
npm run build
```

结果：构建通过，保留既有 Sass / Rollup / chunk size 警告。

FastAPI 启动验证通过，启动日志到达 `AgentForge startup complete`；本地 health degraded 来自数据库、RabbitMQ、Redis 等依赖服务未启动，不是本轮代码启动错误。

TASK-034 文档任务以文档一致性检查为主：

```bash
git diff --check
rg -n "AI Runtime|ModelRoute|AgentProfile|SkillRuntime|EvalFeedback" docs MEMORY.md CLAUDE.md
```

## 4. 关键收获

- 后台配置页不能只是 CRUD。Agent、模型、Skill 和治理策略必须进入 StageRuntime，才能成为平台能力。
- AI 行为要先记录事实，再追求自动优化。EvalEvent 第一版不做复杂评分，但能让后续迭代有真实数据。
- 文档必须区分“历史架构思想”和“当前运行时事实”。Harness 六层仍有价值，但产品主链路应以 Project-first AI Runtime 为准。
- 高风险行为的判断应在服务端策略中表达，前端只展示策略结果，避免多个页面各自实现风险判断。

## 5. 遗留风险

| 风险 | 当前状态 | 建议后续 |
|------|----------|----------|
| Stage 级 Skill 白名单 | TASK-035 已完成 StageSkillPolicy 工具过滤，StageRuntime 会按阶段策略、Agent allowlist 和 SkillRuntimeSpec permissions 过滤 tools | 后续可做高风险 Skill 临时授权 |
| LLM token/cost 明细 | ModelRoute 已进入运行时，EvalEvent 有 token/cost 字段；LLMProvider 级细粒度写入还可继续增强 | 在 LLM 调用完成后写入 `llm_completed` EvalEvent |
| Artifact 运行时引用 | EvalEvent 已记录 AgentProfile/ModelRoute/Skill/Delivery；Artifact 表自身尚未持久化完整运行时引用 | 如前端需要按 Artifact 展示生成来源，再补 Artifact 字段或关联表 |
| MCP 权限归一化 | TASK-036 已完成 MCP RuntimeSpec adapter；未声明 permissions 的 MCP 默认按高风险处理 | 后续可做 MCP 管理 UI |
| 本地依赖健康 | FastAPI 可启动，但 health 在未启动数据库、RabbitMQ、Redis 时 degraded | 开发环境启动脚本继续提示依赖状态 |

## 6. 后续建议

TASK-035 已完成 Stage 级 SkillPolicy 编排，让 `StageDefinition.skill_policy_key`、`AgentProfile.allowed_skill_names` 和 `SkillRuntimeSpec.permissions` 开始决定每个阶段可用工具集合。TASK-036 进一步完成 MCP RuntimeSpec adapter。下一步更适合推进内置 Skill RuntimeSpec 补齐或高风险 Skill 临时授权。
