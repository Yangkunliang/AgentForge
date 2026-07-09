# TASK-030: LLM Provider / Model / Credential / Route

```yaml
id: AIARCH-P0-004
module: llm
priority: P0
title: LLM Provider / Model / Credential / Route
related_requirements:
  - R-004
deliverable:
  - ModelRouter
  - Provider / Model / Credential / Route 数据结构
  - LLM 设置 API 与前端页面
  - 密钥脱敏和安全测试
acceptance:
  - 后台能配置模型供应商、密钥、模型路由
  - StageRuntime 能解析模型路由
  - API 不返回明文密钥
status: todo
```

## 背景

AgentForge 需要长期支持多个模型供应商和不同阶段模型策略。单一全局模型配置会限制迭代，也不利于成本和失败兜底治理。

## 范围

- Provider：供应商和基础 endpoint。
- Model：模型能力、上下文长度、价格元数据。
- Credential：密钥或密钥引用，API 只返回 masked 信息。
- Route：阶段或 Agent 使用的模型路线和 fallback。
- Policy：预算、重试、超时。

## 实施 checklist

- 盘点现有 `src/agent_forge/llm/provider.py` 和 `src/agent_forge/models/api_key.py`。
- 确定复用还是新增模型表。
- 新增 ModelRouter。
- 迁移旧 LLM 配置为默认 route。
- StageRuntime 接入 ModelRouter。
- LLM 设置页从“单模型配置”升级为“Provider / Credential / Route”。
- 增加密钥 masked 返回和日志防泄漏测试。

## 验收标准

- 可以配置 OpenAI、Anthropic 或其他 provider 的占位结构。
- 可以设置某个阶段默认使用某个 route。
- route 不可用时能按 fallback 执行或明确失败。
- 后端日志和 API 响应不出现明文 API Key。

## 验证

```bash
uv run --extra dev pytest tests/api/test_cost.py tests/api/test_auth.py
```

```bash
uv run --extra dev pytest tests/api/test_llm_routes.py
```

```bash
npm run build
```

前端命令在 `/Users/yangkl/AgentForge/web` 下执行。
