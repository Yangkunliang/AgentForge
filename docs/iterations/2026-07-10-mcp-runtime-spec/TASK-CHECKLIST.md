# TASK-036 Checklist

| 状态 | 任务 | 验收 |
|------|------|------|
| ✅ | 梳理 MCP 注册链路 | 明确 MCPClientPool 在 `_register_to_skill_registry()` 注册工具 |
| ✅ | 增加红灯测试 | 测试覆盖 permissions 配置、RuntimeSpec 注册和 StagePolicy 过滤 |
| ✅ | 实现 MCP 权限归一 | `MCPServerConfig.permissions` 支持声明和默认高风险 fallback |
| ✅ | 实现 MCP RuntimeSpec Adapter | `mcp_<server>` 注册时写入 `source_type=mcp`、`executor_kind=mcp` 和工具列表 |
| ✅ | 同步文档 | AI Runtime、安全、架构、索引和迭代文档更新 |
| ✅ | 完整验证 | MCP/Skill/Pipeline 相关测试、全量 pytest、前端 build、FastAPI 启动 |
| ✅ | 提交合并 | commit、push、合并 main、push main |

## 后续建议

- TASK-037 可继续把内置 Skill 也补齐 RuntimeSpec，避免 `code-executor`、`http-request` 等内置工具仅靠调用前校验。
- MCP UI 可在后续展示权限来源：用户显式声明 / 未声明高风险默认。
