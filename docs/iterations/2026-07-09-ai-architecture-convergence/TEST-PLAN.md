# AI 架构收敛测试计划

## 1. 测试目标

本测试计划用于保证 AI 架构收敛不是只增加抽象，而是让现有核心闭环更稳定：

- Project / Pipeline / Stage / Agent / Skill / Artifact / Delivery 不回归。
- Agent、模型、Skill 的运行时选择可追溯。
- 高风险操作可确认、可审计。
- 执行指标和失败原因可记录。
- 前端构建和后端启动保持可用。

## 2. 分层测试策略

### 2.1 单元测试

覆盖：

- Pipeline Catalog 解析。
- AgentResolver 选择优先级。
- ModelRouter 兜底策略。
- Skill Manifest 校验。
- SkillPolicy 权限判断。
- GovernancePolicy 确认策略。
- EvalEvent 构造和聚合。

### 2.2 API 测试

覆盖：

- `/api/pipeline/catalog`
- `/api/agents/runtime-options`
- `/api/llm/*`
- `/api/skills/import/*`
- `/api/evaluation/*`
- PipelineRun 阶段执行和确认 API。

### 2.3 集成测试

覆盖一条完整链路：

```text
创建 Project
  -> 创建 Session
  -> 发送需求
  -> 生成 PipelineRun
  -> 选择 AgentProfile
  -> 选择 ModelRoute
  -> 执行 Skill
  -> 生成 Artifact
  -> 触发确认
  -> Delivery
  -> 记录 EvalFeedback
```

### 2.4 前端构建和 E2E

覆盖：

- Pipeline 阶段从后端 catalog 渲染。
- Agent 创建后能在运行时配置里选择。
- LLM 设置页能配置 Provider / Credential / Route。
- Skill 安装页能展示导入预览、权限和安装状态。
- Chat / Artifact / ConfirmCard 不回归。

## 3. 基础验证命令

后端全量测试：

```bash
uv run --extra dev pytest
```

后端启动验证：

```bash
PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18090
```

前端构建：

```bash
npm run build
```

前端 E2E：

```bash
npm run test:e2e
```

注意：前端命令在 `/Users/yangkl/AgentForge/web` 下执行。

## 4. 任务级验证矩阵

| 任务 | 必跑测试 | 额外验证 |
|------|----------|----------|
| TASK-027 | 文档链接检查、`git diff --check` | 架构对象是否覆盖完整链路 |
| TASK-028 | `tests/api/test_pipeline_runs.py`、`tests/pipeline/test_runtime.py` | 前端 build；阶段 catalog API 响应检查 |
| TASK-029 | `tests/api/test_agents.py`、`tests/pipeline/test_runtime.py` | 执行记录包含 agent_profile_id |
| TASK-030 | `tests/api/test_cost.py`、新增 llm route 测试 | 密钥不明文返回、不进入日志 |
| TASK-031 | `tests/api/test_skills.py`、`tests/skills/test_dispatcher.py` | 外部 Skill 权限负向用例 |
| TASK-032 | `tests/harness/test_governance.py`、`tests/api/test_pipeline_runs.py` | 高风险动作进入 waiting_confirmation |
| TASK-033 | 新增 evaluation API 测试、dashboard 聚合测试 | PipelineRun 结束后有 EvalEvent |
| TASK-034 | 文档链接检查、`git diff --check` | docs/README、MEMORY、CLAUDE 与架构一致 |

## 5. 人工验收点

### 5.1 运行时可解释性

打开某个 PipelineRun，应能看清：

- 需求类型。
- 当前阶段。
- 使用的 Agent。
- 使用的模型路由。
- 可调用 Skill。
- 输出 Artifact。
- 确认和交付状态。

### 5.2 配置闭环

后台配置 Agent、ModelRoute、Skill 后，新会话执行必须能体现配置影响。

### 5.3 安全闭环

以下操作必须被阻止或确认：

- 未授权本地目录读取。
- 未声明权限的第三方 Skill 调用。
- 明文返回 API Key。
- 高风险写回。
- 技术选型引入新中间件。

### 5.4 反馈闭环

一次执行结束后，至少能看到：

- 成功或失败。
- 阶段耗时。
- 模型路由。
- Skill 调用结果。
- Artifact 采纳或交付状态。

## 6. 回归风险清单

| 风险 | 回归信号 |
|------|----------|
| Stage Catalog 切换导致旧会话渲染失败 | Pipeline 页面空白或阶段顺序错乱 |
| AgentResolver 默认值错误 | 无 Agent 时执行失败 |
| ModelRouter 迁移失败 | 本地默认模型不可用 |
| SkillPolicy 过严 | 内置 Skill 无法调用 |
| Governance 策略过宽 | 高风险写回未确认 |
| Eval 写入异常 | PipelineRun 成功但后台 500 |

## 7. 完成标准

每个 TASK 完成时必须满足：

- 对应任务文件状态更新为 `done`。
- 相关测试通过。
- 涉及后端路由或配置的任务通过 uvicorn 启动验证。
- 涉及前端的任务通过 `npm run build`。
- 相关架构文档和索引已同步。
- 单独 commit，并在合并 main 后进入下一任务。
