# Skill Engine — 产品需求文档

**迭代版本**：2026-06-22-skill-engine  
**状态**：进行中  
**背景**：天气查询测试发现 LLM 返回捏造数据，根本原因是 LLM tool_use 调用循环缺失；Agent 没有真正执行任何 Skill。

---

## 1. 问题陈述

当前 `_run_task_and_update_message` 直接调用 `llm.stream_complete(description)`，LLM 只能凭训练数据生成文本，无法访问真实外部数据（天气、搜索、汇率等）。结果就是天气被"捏造"。

## 2. 用户故事

| # | 故事 | 优先级 |
|---|------|--------|
| US-01 | 用户问天气，Agent 自动调用天气 Skill 返回实时数据 | P0 |
| US-02 | 用户问最新新闻，Agent 调用 web_search Skill | P0 |
| US-03 | 管理员可从 Skill 市场（clawhub.ai、GitHub）一键安装 Skill | P1 |
| US-04 | 管理员可查看已安装 Skill 列表，点击启用/禁用 | P1 |
| US-05 | 开发者可按 skill.md 规范编写自定义 Skill 并注册 | P1 |
| US-06 | SSE 流中可以看到 `skill_called` / `skill_result` 事件（前端可选展示） | P2 |

## 3. 功能需求

### 3.1 Skill 执行引擎（核心，解决捏造问题）

- 每次 chat 调用前，从 DB 加载当前 session 对应 Agent 已启用的 Skill 列表
- 将 Skill 的 tool 定义注入到 LLM 请求的 `tools` 参数
- 实现 **ReAct 循环**：LLM → 判断是否有 tool_call → 执行 Skill → 把结果追加为 `tool` role message → 再次调用 LLM → 直到 LLM 不再调用工具
- 循环最多执行 `SKILL_MAX_ROUNDS`（默认 5）轮，防止死循环
- 每次 Skill 调用通过 SSE 推送 `skill_called` 和 `skill_result` 事件

### 3.2 内置 Skill：天气查询

- 使用 [Open-Meteo](https://open-meteo.com/)（免费、无需 API Key）
- 支持城市名查询：先 geocoding → 再 weather API
- Tool 定义：`get_weather(city: str, unit?: "celsius"|"fahrenheit")`
- 返回：当前温度、天气描述、湿度、风速、未来 3 天预报

### 3.3 Skill 市场集成

- 支持浏览来源：
  - **clawhub.ai** (`CLAWHUB_API_BASE` env，Skill 目录页面)  
  - **GitHub Topic** (`agentforge-skill` topic 标签)
  - **本地目录** (`skills/user/` 下自定义 Skill)
- 安装来源类型：
  - GitHub URL：`https://github.com/owner/repo`
  - PyPI 包名
  - 本地路径
- 安装状态实时查询（轮询 `/skills/install/{id}`）

### 3.4 Skill 启用/禁用

- Agent 可绑定多个 Skill（通过 `agent_skills` 表）
- 每个 Skill 可在 Agent 级别启用/禁用（不影响全局注册）
- 全局也可启用/禁用（`Skill.enabled` 字段）

## 4. 非功能需求

- Skill 执行超时：单次 Skill 调用 ≤ 30s
- ReAct 循环总时长 ≤ 120s
- Skill 执行结果缓存：相同参数 5 分钟内复用（可选，Redis）
- 安全：Skill 执行在独立沙箱（Phase 2，当前 Phase 1 仅 Python 函数调用）
