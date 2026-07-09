# AI 架构收敛任务清单

## 1. 用户故事覆盖矩阵

| 用户故事 | TASK-027 | TASK-028 | TASK-029 | TASK-030 | TASK-031 | TASK-032 | TASK-033 | TASK-034 |
|----------|----------|----------|----------|----------|----------|----------|----------|----------|
| US-1 阶段和产物可复盘 | yes | yes | yes | partial | partial | yes | yes | yes |
| US-2 自动选择 Agent、模型、Skill | yes | yes | yes | yes | yes | partial | yes | yes |
| US-3 高风险修改前确认 | partial | partial | partial | partial | yes | yes | yes | yes |
| US-4 Skill、密钥、Agent 可治理 | yes | partial | yes | yes | yes | yes | yes | yes |
| US-5 执行质量可评估 | partial | partial | yes | yes | yes | yes | yes | yes |

## 2. 任务索引

| 任务 | 标题 | 模块 | 优先级 | 依赖 | 状态 |
|------|------|------|--------|------|------|
| [TASK-027](TASK-027.md) | AI Runtime Baseline 与契约文档 | architecture | P0 | none | done |
| [TASK-028](TASK-028.md) | Pipeline Stage Catalog 后端唯一事实源 | pipeline | P0 | TASK-027 | done |
| [TASK-029](TASK-029.md) | Agent Profile 运行时绑定 | agents, pipeline | P0 | TASK-027, TASK-028 | done |
| [TASK-030](TASK-030.md) | LLM Provider / Model / Credential / Route | llm, settings | P0 | TASK-027, TASK-029 | done |
| [TASK-031](TASK-031.md) | 第三方 Skill 导入与运行时闭环 | skills | P1 | TASK-027, TASK-030 | done |
| [TASK-032](TASK-032.md) | Governance 与人工确认策略引擎 | governance, pipeline | P1 | TASK-028, TASK-031 | todo |
| [TASK-033](TASK-033.md) | Eval Feedback 执行质量反馈闭环 | evaluation, dashboard | P1 | TASK-029, TASK-030, TASK-031, TASK-032 | todo |
| [TASK-034](TASK-034.md) | 架构文档收敛与迁移清理 | docs | P2 | TASK-028, TASK-029, TASK-030, TASK-031, TASK-032, TASK-033 | todo |

## 3. 推荐执行顺序

```text
TASK-027
  -> TASK-028
    -> TASK-029
      -> TASK-030
        -> TASK-031
          -> TASK-032
            -> TASK-033
              -> TASK-034
```

如果需要并行，最多允许：

- `TASK-031` 的 Manifest 解析与 `TASK-030` 的后台页面草案并行，但最终合并必须等 Model Route 契约确定。
- `TASK-034` 的文档盘点可以提前做，但最终文档收敛必须等代码任务完成。

## 4. 阶段里程碑

### Milestone A: 运行时骨架收敛

包含：

- TASK-027
- TASK-028

验收：

- AI Runtime Contract 明确。
- Pipeline 阶段定义由后端提供。
- 前端不再依赖重复阶段常量作为核心事实源。

### Milestone B: Agent 和模型进入运行时

包含：

- TASK-029
- TASK-030

验收：

- Agent 创建后能被运行时选择和追踪。
- 模型密钥、模型、路由策略可管理。
- StageRuntime 能解析 AgentProfile 和 ModelRoute。

### Milestone C: 扩展能力与风险治理

包含：

- TASK-031
- TASK-032

验收：

- 第三方 Skill 有导入、权限、注册、审计闭环。
- 人工确认和高风险动作有统一策略入口。

### Milestone D: 长期反馈闭环

包含：

- TASK-033
- TASK-034

验收：

- 执行质量、成本、延迟、失败原因可结构化记录。
- 架构文档和真实代码链路一致。

## 5. 提交节奏

- 每完成一个 TASK，单独更新对应 `TASK-NNN.md` 状态为 `done`。
- 每个 TASK 使用单独 commit。
- 如果需要开发分支，命名建议使用 `feature/task-027-ai-runtime-baseline` 这类前缀，不使用 `codex` 前缀。
- 每个 TASK 合并 main 后再进入下一个 TASK，避免阶段 2、3 被遗忘或偏航。
