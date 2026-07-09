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
status: done
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

- [x] 盘点现有 `src/agent_forge/llm/provider.py` 和 `src/agent_forge/models/api_key.py`。
- [x] 确定新增 LLM Provider / Model / Credential / Route 表，不复用服务端访问 `APIKey`。
- [x] 新增 `src/agent_forge/llm/router.py` ModelRouter。
- [x] 保留旧全局 LLM 配置作为 legacy fallback route。
- [x] StageRuntime 接入 ModelRouter，并记录 `model_route_key/name/source` 与 `model_name`。
- [x] LLM 设置页从“单模型配置”升级为“Provider / Model / Credential / Route”。
- [x] 增加密钥 masked 返回、API 不泄漏明文和 fallback route 测试。

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

## 完成说明

- 新增 `llm_providers`、`llm_models`、`llm_credentials`、`llm_routes` 结构化配置表。
- `LLMCredential.encrypted_secret` 使用服务端加密，API 仅返回 `masked_secret`。
- `ModelRouter` 按 requested route 解析，route 不可用时尝试 `fallback_route_keys`，最终退回 legacy settings。
- `LLMConfig` 增加 `api_key`、`api_base`、`provider_key`，LiteLLM 调用按 route 注入配置。
- `/api/v1/llm/providers`、`/api/v1/llm/models`、`/api/v1/llm/credentials`、`/api/v1/llm/routes` 已落地。
- StageRuntime 会将 ModelRoute 上下文注入 SkillExecutionEngine，且不包含明文 key。
