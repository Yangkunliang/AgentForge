# TASK-029: Agent Profile 运行时绑定

```yaml
id: AIARCH-P0-003
module: agents
priority: P0
title: Agent Profile 运行时绑定
related_requirements:
  - R-003
deliverable:
  - src/agent_forge/agents/resolver.py
  - StageRuntime agent_profile_id 记录
  - Agent runtime API
  - tests/api/test_agents.py
  - tests/pipeline/test_runtime.py
acceptance:
  - Agent 创建后能被运行时选择
  - 执行记录能追溯使用的 AgentProfile
  - 支持阶段默认、项目默认、用户覆盖的优先级
status: done
```

## 背景

当前后台可以创建 Agent，但用户会自然追问：创建后作用在哪里。这个任务让 Agent 从配置对象变成 StageRuntime 的运行时决策对象。

## 选择优先级

建议顺序：

```text
用户在本次 Stage 手动指定
  -> Project agent policy
  -> StageDefinition.default_agent_selector
  -> 系统默认 Agent
```

## 范围

- 设计 AgentResolver。
- 将 Agent capabilities、allowed skills、default model route 纳入运行时。
- PipelineRun / StageState / execution event 记录 agent_profile_id。
- 前端展示当前阶段使用的 Agent。

## 实施 checklist

- 梳理现有 Agent 模型字段是否足够。
- 如字段不足，补充能力、默认模型路由、Skill 白名单、启用状态。
- 新增 AgentResolver。
- StageRuntime 调用 AgentResolver。
- SkillExecutionEngine 接收 agent_name / agent_profile_id。
- API 返回运行时可选 Agent。
- 前端在阶段详情或执行过程展示 Agent。

## 验收标准

- 无 Agent 配置时仍能使用系统默认 Agent。
- 禁用 Agent 不会被运行时选择。
- 执行记录能追溯 agent_profile_id。
- 用户能理解 Agent 是作用于阶段执行，而不是孤立配置。

## 验证

```bash
uv run --extra dev pytest tests/api/test_agents.py tests/pipeline/test_runtime.py
```

```bash
uv run --extra dev pytest tests/agents/test_resolver.py tests/api/test_agents.py tests/pipeline/test_runtime.py tests/skills/test_engine_context.py
```

```bash
npm run build
```

前端命令在 `/Users/yangkl/AgentForge/web` 下执行。

后端启动验证：

```bash
JWT_SECRET_KEY=task029-local-startup-secret uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18091
```
