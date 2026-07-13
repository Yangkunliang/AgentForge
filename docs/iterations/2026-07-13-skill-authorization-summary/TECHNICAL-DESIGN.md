# TASK-041 技术设计：高风险 Skill 授权聚合指标

## 输出结构

`EvaluationService.get_summary()` 新增：

```json
{
  "skill_authorizations": {
    "required": 2,
    "granted": 1,
    "grant_rate": 0.5,
    "by_skill": [
      {
        "skill_name": "code-executor",
        "required": 1,
        "granted": 1,
        "grant_rate": 1.0
      }
    ],
    "by_permission": [
      {
        "permission": "shell",
        "required": 1,
        "granted": 1,
        "grant_rate": 1.0
      }
    ]
  }
}
```

## 统计规则

- `required` 来自 `event_type=skill_authorization_required`。
- `granted` 来自 `event_type=skill_authorization_granted`。
- `grant_rate = granted / required`，无 required 时为 `0.0`。
- 权限从 `metadata.permissions` 读取，只统计字符串值。

## 边界

- 不把普通 `skill_called` / `skill_failed` 混入授权指标。
- 不对事件正文做自由文本解析。
- 不改变 Dashboard API 既有字段，只增加新字段。
