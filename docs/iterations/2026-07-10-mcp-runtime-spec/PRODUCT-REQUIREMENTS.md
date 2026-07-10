# TASK-036 MCP RuntimeSpec 权限归一

## 背景

TASK-035 已让 StageRuntime 在调用 SkillExecutionEngine 前按 `StageDefinition.skill_policy_key`、`AgentProfile.allowed_skill_names` 和 `SkillRuntimeSpec.permissions` 过滤 LLM 可见工具。但 MCP Server 启动后虽然会把工具注册进 SkillRegistry，却没有写入 `runtime_spec`，导致外部 MCP 工具无法被同一套 StageSkillPolicy、权限风险和审计语义准确识别。

## 用户价值

面向全栈开发工程师，MCP 是连接第三方开发工具、代码仓库、数据库和云服务的重要扩展方式。平台必须允许扩展，同时不能让未知外部工具绕过 AI Runtime 的权限边界。

## 范围

- MCP 配置支持声明 `permissions`。
- 未声明权限的 MCP Server 默认按未知高风险处理。
- MCP tool 注册到 SkillRegistry 时生成 `source_type=mcp` 的 `SkillRuntimeSpec`。
- StageSkillPolicy 能基于 MCP RuntimeSpec 权限过滤 LLM 可见工具。

## 不做

- 不实现 MCP 市场导入 UI。
- 不实现逐个 MCP tool 的细粒度权限编辑。
- 不改变 MCP SDK 连接、调用和返回值处理逻辑。

## 验收标准

- 配置 `permissions=["filesystem"]` 的 MCP Server 注册后，SkillRegistry 可读取 `mcp_<server>` 的 RuntimeSpec。
- 默认 StageSkillPolicy 不暴露 `filesystem` MCP 工具。
- 未声明 permissions 的 MCP 配置不会被当作低风险工具。
- 相关架构、安全和索引文档同步。
