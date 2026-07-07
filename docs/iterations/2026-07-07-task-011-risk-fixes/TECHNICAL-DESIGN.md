# TASK-011 Advanced Settings and Risk Fixes

## 背景

本轮继续推进 `TASK-011`：让高级设置面板从静态 UI 变成真实执行上下文。用户在对话前选择的需求类型、上下文线索、阶段跳过设置，必须进入前端状态层、请求 payload、后端接口和 Agent system prompt。

同时在实现前审视当前产品/技术设计，发现若干会影响启动、接口一致性和用户信任的风险。本轮只修正与 TASK-011 或启动可用性直接相关的项，较大的 Project 后端化留作独立架构迭代。

## 已修正风险

| 风险 | 表现 | 修正 |
|---|---|---|
| 高级设置是假动作 | `IntentSelector` 只存在于 `Index.vue` 局部 ref，`ContextChips` 是硬编码，`StagePreview` 只读，发送请求只带 `content` | 新增 `useAdvancedSettingsStore`，持久化 intent/context/stage，并通过 `ChatAdvancedPayload` 发送到后端 |
| Agent 不知道用户选择的需求类型 | 后端 `ChatRequest` 不接收 intent/context/stage，执行引擎无法感知用户选择 | 扩展 `ChatRequest`，将高级设置格式化为 `advanced_context` 注入 `SkillExecutionEngine` system prompt |
| 上下文线索容易被误解为已读取文件 | 只传文件名可能导致 Agent 假设已经看到文件内容 | system prompt 明确说明上下文条目只是关注线索，需要真实内容时必须调用工具或请求授权 |
| 沙箱配置字段不一致 | `sandboxes.py`、`reclaimer.py`、`coder.py` 传入 `cube_sandbox_api_key`，但配置类没有该字段；工厂 `cubesandbox_api` 分支引用未定义 `api_key` | `CubeSandboxConfig` 新增 `cube_sandbox_api_key`，`SandboxProviderFactory.create()` 明确接收 `api_key` |
| API 路由双前缀 | `memory.router`、`sandboxes.router` 自带 `/api/...` 前缀，`main.py` 又统一加 `/api/v1`，真实路径会变成 `/api/v1/api/...` | 子路由移除硬编码 API 前缀，统一由 `main.py` 挂载到 `/api/v1/memory` 和 `/api/v1/sandboxes` |

## 后续风险

| 风险 | 影响 | 建议拆分 |
|---|---|---|
| Project/Mount/Artifact 仍未成为后端一等模型 | 产品设计要求 Project-first，但当前后端仍以 Session/Task/Message 为主，项目管理页更接近静态原型 | 新增独立 `TASK-012` 或 Project persistence 迭代，包含数据库迁移、API、前端项目管理和 Session 归属 |
| `uv.lock` 与 `pyproject.toml` 对 E2B 依赖不同步 | `pyproject.toml` 声明 `e2b-code-interpreter`，但锁文件缺少对应包，`uv run --extra dev` 会尝试重新解析并下载依赖 | 在网络稳定环境执行一次受控 `uv lock`，独立提交锁文件同步 |
| 沙箱测试仍依赖 mock executor | 当前 `tests/sandbox/test_api_routes.py` 使用 `MockSandboxExecutor` 测 REST 路由行为，能测接口但不能覆盖真实 E2B/CubeSandbox 集成 | 保留单元测试，新增可选集成测试，只有配置 `E2B_API_KEY` 时运行 |

## 实现边界

- 不新增 Project/Mount/Artifact 数据库表。
- 不实现文件树浏览器、Git 分支下拉或真实代码库授权。
- 不让 Agent 根据 intent 做完整 Harness 路由重排，本轮仅把用户选择作为 system prompt 执行上下文。
- 不改变现有聊天 SSE 协议，只扩展发送请求 payload。
