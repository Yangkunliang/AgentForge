# TASK-037 Checklist

| 状态 | 任务 | 验收 |
|------|------|------|
| ✅ | 梳理内置 Skill 注册路径 | 明确 `register_builtin_skills()` 未传 runtime_spec |
| ✅ | 增加红灯测试 | 覆盖内置 RuntimeSpec、`external_side_effect` 风险和默认过滤 |
| ✅ | 扩展权限模型 | `external_side_effect` 进入允许枚举并归为 high risk |
| ✅ | 补齐内置 RuntimeSpec | 五个内置 Skill 注册到 DB 和 SkillRegistry 时都有 RuntimeSpec |
| ✅ | 同步文档 | AI Runtime、安全、API、架构、索引和迭代文档更新 |
| ✅ | 完整验证 | 相关测试、全量 pytest、前端 build、FastAPI 启动 |
| ✅ | 提交合并 | commit、push、合并 main、push main |

## 后续建议

- TASK-038 可设计高风险 Skill 临时授权/确认恢复机制，让用户明确批准某一轮执行可见 `code_executor` 或 `http_request`。
- 后续可把 `http_request` 拆成只读 GET 和有副作用方法两类工具，进一步降低默认过滤的粗粒度。
