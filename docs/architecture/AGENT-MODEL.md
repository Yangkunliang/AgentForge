# Agent 领域模型

本文档描述 AgentForge 产品内部的 Agent 概念、类型、能力模型和协作机制。仓库级 Agent 工作规范见根目录 `AGENTS.md`。

## 1. Agent 定义

**Agent** 是 AgentForge 框架中的核心执行单元，基于 LLM 的智能体，具备以下能力：

- **感知**：接收任务输入，理解任务目标
- **思考**：分析任务、规划执行步骤
- **执行**：调用 Skill 完成任务
- **协作**：与其他 Agent 协商分工

**公式（概念层）**：`Agent = Model + Harness + Skills`

**当前运行时落地（TASK-029～TASK-033）**：

```text
Agent 管理态配置
  -> AgentResolver
  -> AgentProfile
  -> StageRuntime
  -> ModelRoute + SkillRuntimeSpec + GovernancePolicy
  -> EvalEvent
```

也就是说，后台 Agent 创建后不再只是展示配置。StageRuntime 会根据用户覆盖、项目默认、阶段默认和系统默认解析 AgentProfile，并把 `agent_profile_id/name/source` 写入 `PipelineStageState` 与 EvalEvent。

## 2. Agent 类型

| 类型 | 描述 | 内置 |
|------|------|------|
| Coder | 代码编写、重构、调试 | ✅ |
| Reviewer | 代码审查、问题发现 | ✅ |
| Researcher | 信息检索、知识整理 | ✅ |
| Planner | 任务拆解、流程规划 | ✅ |
| Custom | 自定义 Agent | — |

## 3. Agent 能力模型

```yaml
Agent:
  id: UUID
  name: string
  description: string
  model: string              # 兼容字段；运行时优先交给 ModelRoute 解析
  capabilities: []          # 能力标签列表
  default_model_route_key: string | null
  allowed_skill_names: []    # 来自 AgentSkill 绑定，参与 StageSkillPolicy 工具过滤
  stage_preferences: {}      # 后续阶段偏好
  status: enum[active, inactive]
  metadata:
    max_concurrency: int    # 最大并发任务数
    timeout: int            # 任务超时时间(秒)
```

## 4. 协作机制

### 4.1 Contract Net 协议（概念保留）

Agent 间通过 Contract Net 协议进行任务协商的概念仍保留，但当前核心开发闭环优先采用 StageRuntime 的单阶段 AgentProfile 解析，而不是多 Agent 实时竞标：

```
1. 发布(Announce)   → 发布者广播任务需求
2. 竞标(Bid)        → 候选者评估并提交方案
3. 评分(Award)      → 发布者评估并选择执行者
4. 执行(Execute)    → 中标者执行任务
5. 结果(Result)     → 返回执行结果
```

### 4.2 降级策略

当主 Agent 失败时，自动切换备选：

```yaml
fallback:
  max_retries: 3
  strategy: sequential      # sequential / parallel
  agents: []               # 备选 Agent 列表
```

## 5. 内置 Agent

### 5.1 Coder

**职责**：代码编写与重构

**能力标签**：`code`, `refactor`, `debug`

**默认 Skill**：
- `write-code`：生成代码
- `review-code`：代码审查
- `fix-bug`：Bug 修复

### 5.2 Reviewer

**职责**：代码质量审查

**能力标签**：`review`, `quality`, `security`

**默认 Skill**：
- `check-style`：代码风格检查
- `check-security`：安全漏洞检测
- `check-performance`：性能分析

### 5.3 Researcher

**职责**：信息检索与整理

**能力标签**：`research`, `search`, `analysis`

**默认 Skill**：
- `web-search`：网络搜索
- `doc-read`：文档阅读理解
- `summarize`：内容摘要

### 5.4 Planner

**职责**：任务规划与分解

**能力标签**：`planning`, `decomposition`, `coordination`

**默认 Skill**：
- `task-split`：任务拆分
- `estimate`：工作量评估
- `schedule`：进度规划

## 6. Agent 注册

Agent 通过 API 或配置注册：

```bash
# 注册 Agent
POST /api/v1/agents
{
  "name": "my-coder",
  "type": "coder",
  "model": "gpt-4",
  "capabilities": ["code", "refactor"],
  "skills": ["write-code", "review-code"]
}

# 列出 Agent
GET /api/v1/agents

# 查询运行时候选
GET /api/v1/agents/runtime/candidates?stage_selector=coder

# 更新 Agent
PUT /api/v1/agents/{id}

# 删除 Agent
DELETE /api/v1/agents/{id}
```

## 7. 状态管理

| 状态 | 说明 |
|------|------|
| `active` | 可接收任务 |
| `inactive` | 暂停服务 |

当前数据库状态以 `active` / `inactive` 为准；`busy` / `error` 可作为后续调度器扩展状态，不是当前 API 契约。

---

*文档版本: v1.1 | 更新日期: 2026-07-10*
