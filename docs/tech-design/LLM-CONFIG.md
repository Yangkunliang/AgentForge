# LLM 配置与设计 (LLM-CONFIG.md)

## 1. 架构设计

### 1.1 Provider 接口
```python
class LLMProvider(Protocol):
    async def chat(self, messages: List[dict], **kwargs) -> str:
        ...
    async def get_token_usage(self) -> dict:
        ...
    async def get_cost(self) -> float:
        ...
```

### 1.2 统一调用流程
```
TaskOrchestrator
    │
    ▼
ModelSelector (根据任务复杂度选择模型)
    │
    ▼
LiteLLMAdapter (统一 API 调用)
    │
    ▼
Provider (OpenAI/Anthropic/Gemini/...)
    │
    ▼
CostTracker (记录 token 和成本)
```

## 2. LiteLLM 配置

### 2.1 模型路由配置
```yaml
# llm_config.yaml
models:
  simple:           # 简单任务
    models:
      - model: "gpt-4o-mini"
        weight: 0.7
      - model: "claude-3-haiku"
        weight: 0.3
  medium:           # 中等任务
    models:
      - model: "gpt-4"
        weight: 0.5
      - model: "claude-3-sonnet"
        weight: 0.5
  complex:          # 复杂任务
    models:
      - model: "gpt-4-turbo"
        weight: 0.4
      - model: "claude-3-opus"
        weight: 0.6

fallback:           # 降级策略
  enabled: true
  max_retries: 3
  retry_delay_ms: 1000
```

### 2.2 环境变量配置
```bash
# .env
LITELLM_MODEL_ROUTE=simple:medium:complex
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GEMINI_API_KEY=xxx
```

## 3. 模型选择策略

### 3.1 自动选择逻辑
```python
def select_model(task):
    """根据任务特征选择模型"""
    complexity = assess_complexity(task.description)
    budget = task.budget
    
    if complexity == "simple":
        return pick_cheapest(models.simple, budget)
    elif complexity == "medium":
        return pick_best_cost_performance(models.medium, budget)
    else:
        return pick_best_quality(models.complex, budget)
```

### 3.2 复杂度评估指标
| 指标 | 简单 (simple) | 中等 (medium) | 复杂 (complex) |
|------|--------------|--------------|---------------|
| 输入长度 | < 500 tokens | < 2000 tokens | > 2000 tokens |
| 所需 Skill 数 | 0 | 1-2 | > 2 |
| 子任务数 | 1 | 2-3 | > 3 |
| 时间敏感度 | 低 | 中 | 高 |

## 4. Fallback 策略

### 4.1 模型降级
```
gpt-4 (主) → gpt-4o-mini (备选) → claude-3-sonnet (最后备选)
```

### 4.2 故障转移
- 超时：> 60s → 切换到更快模型
- 429 (限流)：等待后重试
- 500 (服务不可用)：切换到备选模型

## 5. Cost 追踪

### 5.1 每次调用记录
```python
{
    "model": "gpt-4",
    "tokens_used": {"prompt": 1200, "completion": 800, "total": 2000},
    "cost_usd": 0.03,
    "duration_ms": 2500,
    "success": True
}
```

### 5.2 每日成本统计
```http
GET /api/v1/cost?date=2026-06-17
```

**响应**:
```json
{
  "date": "2026-06-17",
  "total_cost_usd": 15.50,
  "model_costs": {
    "gpt-4": 10.20,
    "gpt-4o-mini": 3.30,
    "claude-3-sonnet": 2.00
  },
  "total_tasks": 50,
  "avg_cost_per_task": 0.31
}
```

## 6. Prompt 管理

### 6.1 System Prompt 模板
```yaml
# prompts/
├── system/
│   ├── coder.yaml
│   ├── reviewer.yaml
│   └── researcher.yaml
└── tasks/
    ├── code_review.yaml
    └── bug_fix.yaml
```

### 6.2 Prompt 模板示例
```yaml
# prompts/system/reviewer.yaml
name: code-reviewer
role: "代码审查专家"
instructions: |
  你是一个资深的代码审查专家。请审查以下代码：
  1. 代码风格和规范
  2. 潜在的安全漏洞
  3. 性能问题
  4. 可维护性
  
  请用以下格式输出：
  - 总体评分: [1-5]
  - 问题列表:
    1. [严重等级] 问题描述
    2. ...
  - 改进建议: ...
```

## 7. 性能优化

### 7.1 缓存策略
- 相同任务的响应缓存（TTL: 1h）
- Prompt 模板缓存
- 模型选择结果缓存

### 7.2 并发控制
- 每个模型最大并发数限制
- 队列管理（超出时排队等待）

```yaml
concurrency:
  gpt-4: 10
  gpt-4o-mini: 50
  claude-3-sonnet: 20
```
