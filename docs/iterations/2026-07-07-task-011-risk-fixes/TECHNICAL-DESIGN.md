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
| `uv.lock` 与 `pyproject.toml` 对 E2B 依赖不同步 | `pyproject.toml` 声明 `e2b-code-interpreter`，但锁文件缺少对应包；全量测试环境还缺 `aiosqlite` | 同步 `uv.lock`，将 `aiosqlite` 加入 dev extra，并安装到本地 `.venv` |
| 沙箱测试依赖已移除的 runtime mock | 旧测试直接导入 `agent_forge.sandbox.mock.MockSandboxExecutor`，全量 pytest 在 collection 阶段失败 | 新增 `tests/sandbox/fakes.py` 的 `InMemorySandboxExecutor`，测试层 fake 与产品运行时 provider 解耦 |
| SQLite 测试库无法创建 PostgreSQL 专属列 | API 测试使用 `sqlite+aiosqlite`，但模型直接使用 `JSONB` / pgvector `Vector`，`Base.metadata.create_all` 失败 | 新增 `JSON_VARIANT`，PostgreSQL 使用 JSONB，SQLite 测试降级 JSON；embedding 列同样在 SQLite 降级 JSON |
| 治理层异步熔断依赖不稳定 | `pybreaker.call_async()` 在当前 Python/依赖组合下引用缺失的 `gen`，导致成功函数也失败 | `CircuitBreaker.call()` 改为显式 await 用户函数，并用同步 pybreaker 调用记录成功/失败 |
| 记忆检索与分块存在边界 bug | `_keyword_search()` 把 SQL 对象误当查询字符串；`user_memories` SQL 假设不存在的字段；chunk overlap 大于 max_size 时死循环 | 明确传入 search query，按表结构生成 SQL；限制 overlap 小于 chunk size，空白文本返回空 chunk |
| HTTP skill 单测依赖外网 | 测试访问 `httpbin.org`，离线或沙箱网络受限时失败 | 用 `monkeypatch` 模拟 `httpx.AsyncClient.request()`，测试保持离线、确定性 |
| system prompt 安全规则不可验证 | 安全测试期望 `SYSTEM_PROMPT_WITH_TOOLS`，但引擎只保留 `SYSTEM_PROMPT`，且缺少明确 platform rules 保护块 | 增加 `SYSTEM_PROMPT_WITH_TOOLS` 兼容常量，并加入用户输入不得覆盖平台规则的 `<platform_rules>` |

## 后续风险

| 风险 | 影响 | 建议拆分 |
|---|---|---|
| Project/Mount/Artifact 仍未成为后端一等模型 | 产品设计要求 Project-first，但当前后端仍以 Session/Task/Message 为主，项目管理页更接近静态原型 | 新增独立 `TASK-012` 或 Project persistence 迭代，包含数据库迁移、API、前端项目管理和 Session 归属 |
| 测试告警仍较多 | 全量 pytest 已通过，但仍有 Pydantic V2 class-based config、pytest 未注册 mark、Starlette TestClient 等废弃告警 | 独立清理 warning 迭代，先注册自定义 marks，再迁移 Pydantic `ConfigDict` |

## 实现边界

- 不新增 Project/Mount/Artifact 数据库表。
- 不实现文件树浏览器、Git 分支下拉或真实代码库授权。
- 不让 Agent 根据 intent 做完整 Harness 路由重排，本轮仅把用户选择作为 system prompt 执行上下文。
- 不改变现有聊天 SSE 协议，只扩展发送请求 payload。
