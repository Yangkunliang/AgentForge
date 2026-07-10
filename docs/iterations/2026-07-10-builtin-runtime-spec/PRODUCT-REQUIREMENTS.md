# TASK-037 内置 Skill RuntimeSpec 补齐

## 背景

TASK-031～TASK-036 已让第三方 Skill 和 MCP 外部工具进入统一 `SkillRuntimeSpec` 权限模型。但内置 Skill 启动时仍只注册 tool_defs 和 executor，没有同步 runtime spec。结果是 StageSkillPolicy 可以过滤外部工具，却无法用同一套机制判断 `http-request`、`update-profile`、`code-executor` 等内置高风险工具。

## 用户价值

终端用户是全栈开发工程师。内置工具往往权限更强，尤其是代码执行、任意 HTTP 请求和账号资料修改。如果内置工具不受同一套运行时契约约束，平台越迭代越容易出现“外部工具安全，内置工具绕过”的结构性风险。

## 范围

- 扩展 Skill 权限枚举，新增 `external_side_effect`。
- 内置 Skill 注册时生成并写入 `SkillRuntimeSpec`。
- 默认 StageSkillPolicy 只暴露低/中风险内置工具：`web_search`、`get_weather`。
- `http_request`、`update_profile`、`code_executor` 默认从 LLM 可见工具列表中过滤。

## 不做

- 不实现高风险 Skill 的临时授权 UI。
- 不做 http method 级动态权限判断。
- 不改变 SkillDispatcher 的调用前权限校验和审计。

## 验收标准

- `register_builtin_skills()` 后，五个内置 Skill 均有 RuntimeSpec。
- `external_side_effect` 被归类为高风险权限。
- 默认 StageSkillPolicy 会过滤 `http_request`、`update_profile`、`code_executor`。
- 相关架构、安全和索引文档同步。
