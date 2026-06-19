# 数据导出 - 训练优化 (DATA-EXPORT.md)

## 1. 设计目标

从多智能体运行数据中收集高质量训练数据，用于优化：
1. **Agent 路由模型**：根据任务描述自动选择最佳 Agent
2. **Skill 模板优化**：优化 Skill 输入参数和 prompt 模板
3. **模型选择策略**：根据任务复杂度选择性价比最高的模型
4. **对话质量分析**：优化 Agent 角色定义和协商策略

## 2. 导出格式

### 2.1 JSONL 格式
每行一条完整记录，包含完整的任务执行链路。

### 2.2 记录结构
```json
{
  "record_id": "uuid",
  "timestamp": "2026-06-17T10:00:00Z",
  "user_id": "user-001",
  "task": {
    "user_input": "审查这个 PR 的代码质量",
    "sub_tasks": [
      {"id": "sub-001", "description": "review_style", "status": "completed"},
      {"id": "sub-002", "description": "review_logic", "status": "completed"}
    ],
    "selected_agent": "reviewer-001",
    "selected_model": "gpt-4",
    "selected_skill": "code-review",
    "agent_dialog": [
      {"from": "coordinator", "to": "reviewer-001", "content": "请审查代码风格"},
      {"from": "reviewer-001", "to": "coordinator", "content": "发现 3 个问题..."}
    ],
    "skill_calls": [
      {"skill": "ruff", "input": "...", "output": "...", "duration_ms": 200}
    ],
    "final_result": "发现 3 个问题...",
    "response_time_ms": 2500,
    "token_usage": {"prompt": 1200, "completion": 800},
    "cost_usd": 0.03,
    "user_feedback": {"thumbs": 1, "rating": 4}
  }
}
```

## 3. 数据收集

### 3.1 自动收集
- 每次任务执行自动记录到 `TaskExecution` 表
- Agent 间对话自动记录到 `Conversation` 表
- 每次 Skill 调用自动记录 input/output/duration

### 3.2 用户反馈
- 提供 thumbs up/down 接口
- 可选评分（1-5 星）
- 可选备注

```http
POST /api/v1/tasks/{task_id}/feedback
Authorization: Bearer <token>

{
  "thumbs": 1,
  "rating": 4,
  "comment": "分析得很到位"
}
```

## 4. 数据脱敏

### 4.1 脱敏规则
| 数据类型 | 脱敏方式 | 示例 |
|----------|----------|------|
| 邮箱 | 保留域名 | `u***@example.com` |
| 手机号 | 保留后 4 位 | `138****1234` |
| 代码片段 | 替换变量名 | `var x` → `var [VAR]` |
| API Key | 删除 | - |

### 4.2 脱敏级别
- **Level 0**: 不脱敏（内部审计）
- **Level 1**: 脱敏 PII 信息（训练数据）
- **Level 2**: 脱敏代码片段（公开数据集）

## 5. 导出 API

### 5.1 手动导出
```http
POST /api/v1/exports
Authorization: Bearer <token>

{
  "type": "training_data",
  "start_date": "2026-01-01",
  "end_date": "2026-06-17",
  "format": "jsonl",
  "delevel": "level_1"
}
```

**响应**:
```json
{
  "export_id": "export-001",
  "status": "processing",
  "total_records": 1500,
  "estimated_size_mb": 50
}
```

### 5.2 查询导出状态
```http
GET /api/v1/exports/{export_id}
```

### 5.3 下载导出文件
```http
GET /api/v1/exports/{export_id}/download
```

## 6. 模型训练用途

### 6.1 Agent 路由训练数据
```json
{
  "input": "审查这个 PR 的代码质量",
  "label": "reviewer-001",
  "features": ["code_related", "security_concern", "high_priority"]
}
```

### 6.2 Model Selection 训练数据
```json
{
  "input": "审查这个 PR 的代码质量",
  "task_complexity": "medium",
  "selected_model": "gpt-4",
  "alternative_models": ["claude-3", "llama-3"],
  "cost": 0.03,
  "quality_score": 4,
  "label": "gpt-4"  // 最高性价比
}
```

### 6.3 Skill 模板优化数据
```json
{
  "skill": "code-review",
  "input": {"code": "def hello(): pass"},
  "output": "建议添加类型注解...",
  "quality_score": 4,
  "label": "optimal_prompt_template"
}
```

## 7. 定期导出

### 7.1 定时任务
- 每天自动脱敏并归档
- 每周生成导出文件
- 每月清理过期数据（可配置保留期）

### 7.2 配置
```yaml
export:
  schedule: "0 2 * * *"  # 每天凌晨 2 点
  retention_days: 365
  delevel: "level_1"
  storage: "/data/exports/"
```
