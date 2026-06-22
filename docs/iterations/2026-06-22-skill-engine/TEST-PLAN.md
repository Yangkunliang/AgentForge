# Skill Engine — 测试计划

**迭代版本**：2026-06-22-skill-engine  
**状态**：进行中  
**创建日期**：2026-06-22

---

## 1. 测试范围

| 模块 | 测试类型 | 负责人 |
|------|---------|--------|
| `agent_forge.skills.weather` | 单元测试 | — |
| `agent_forge.skills.web_search` | 单元测试 | — |
| `agent_forge.skills.http_request` | 单元测试 | — |
| `agent_forge.skills.dispatcher` | 单元测试 | — |
| `agent_forge.skills.engine` | 集成测试 | — |
| `agent_forge.mcp.client` | 单元测试 | — |
| `agent_forge.mcp.config` | 单元测试 | — |
| `/api/v1/tools/web-search` | API 测试 | — |
| `/api/v1/skills` | API 测试 | — |

---

## 2. 测试场景

### 2.1 内置 Skill：天气查询 (`get_weather`)

| # | 场景 | 输入 | 预期结果 | 优先级 |
|---|------|------|---------|--------|
| W-01 | 查询有效城市天气 | `get_weather(city="Beijing")` | 返回温度、天气描述、湿度、风速 | P0 |
| W-02 | 查询无效城市 | `get_weather(city="InvalidCityXYZ")` | 返回错误信息，不崩溃 | P0 |
| W-03 | 查询中文城市名 | `get_weather(city="上海")` | 正确识别并返回天气 | P0 |
| W-04 | 华氏度单位 | `get_weather(city="Beijing", unit="fahrenheit")` | 返回华氏度温度 | P1 |
| W-05 | 默认单位（摄氏度） | `get_weather(city="Beijing")` | 返回摄氏度温度 | P1 |
| W-06 | 网络超时 | 模拟 Open-Meteo API 超时 | 返回错误信息，不阻塞 | P1 |

### 2.2 内置 Skill：网络搜索 (`web_search`)

| # | 场景 | 输入 | 预期结果 | 优先级 |
|---|------|------|---------|--------|
| S-01 | 正常搜索 | `web_search(query="Python 3.12", max_results=3)` | 返回 1-3 条搜索结果 | P0 |
| S-02 | 空查询 | `web_search(query="", max_results=1)` | 返回空列表，不崩溃 | P0 |
| S-03 | 特殊字符查询 | `web_search(query="C++ 编程")` | 正确编码并返回结果 | P1 |
| S-04 | 搜索结果限制 | `web_search(query="AI", max_results=1)` | 最多返回 1 条结果 | P1 |
| S-05 | DuckDuckGo API fallback | HTML 搜索失败 | 自动切换到 API 搜索 | P1 |
| S-06 | SearxNG 配置 | 设置 `SEARXNG_URL` 环境变量 | 使用 SearxNG 搜索 | P2 |

### 2.3 内置 Skill：HTTP 请求 (`http_request`)

| # | 场景 | 输入 | 预期结果 | 优先级 |
|---|------|------|---------|--------|
| H-01 | GET 请求成功 | `http_request(url="https://httpbin.org/get")` | 返回 200，包含 body | P0 |
| H-02 | POST 请求成功 | `http_request(url="https://httpbin.org/post", method="POST", body={"key": "value"})` | 返回 200，包含请求 body | P0 |
| H-03 | 请求参数 | `http_request(url="https://httpbin.org/get", params={"foo": "bar"})` | URL 包含查询参数 | P1 |
| H-04 | 请求头 | `http_request(url="https://httpbin.org/headers", headers={"X-Custom": "test"})` | 返回包含自定义头 | P1 |
| H-05 | 请求超时 | `http_request(url="https://httpbin.org/delay/10", timeout=1)` | 返回超时错误 | P0 |
| H-06 | SSRF 防护 - localhost | `http_request(url="http://localhost:8000")` | 拒绝访问内网地址 | P0 |
| H-07 | SSRF 防护 - 127.0.0.1 | `http_request(url="http://127.0.0.1:3000")` | 拒绝访问内网地址 | P0 |
| H-08 | SSRF 防护 - 192.168 | `http_request(url="http://192.168.1.100")` | 拒绝访问内网地址 | P0 |
| H-09 | SSRF 防护 - 10.x | `http_request(url="http://10.0.0.1")` | 拒绝访问内网地址 | P0 |
| H-10 | 不支持的协议 | `http_request(url="ftp://example.com")` | 返回协议不支持错误 | P1 |
| H-11 | 无效 URL | `http_request(url="not-a-url")` | 返回格式错误 | P1 |
| H-12 | 连接失败 | `http_request(url="http://nonexistent-domain.invalid")` | 返回连接失败错误 | P1 |

### 2.4 SkillDispatcher

| # | 场景 | 输入 | 预期结果 | 优先级 |
|---|------|------|---------|--------|
| D-01 | 调用已注册工具 | `invoke("get_weather", {"city": "Beijing"})` | 返回工具执行结果 | P0 |
| D-02 | 调用未注册工具 | `invoke("nonexistent_tool", {})` | 返回错误信息 | P0 |
| D-03 | 工具执行超时 | 慢执行函数（>30s） | 返回超时错误 | P0 |
| D-04 | 工具执行异常 | 执行函数抛出异常 | 返回异常信息 | P0 |
| D-05 | SSE 事件回调 - skill_called | 调用工具时传入 on_event | 触发 skill_called 事件 | P1 |
| D-06 | SSE 事件回调 - skill_result | 工具执行完成 | 触发 skill_result 事件 | P1 |

### 2.5 SkillRegistry

| # | 场景 | 输入 | 预期结果 | 优先级 |
|---|------|------|---------|--------|
| R-01 | 注册 Skill | `register("test-skill", tool_defs, executors)` | 注册成功 | P0 |
| R-02 | 获取已注册工具 | `get_tool_defs()` | 返回所有工具定义 | P0 |
| R-03 | 获取执行函数 | `get_executor("get_weather")` | 返回对应执行函数 | P0 |
| R-04 | 获取不存在的执行函数 | `get_executor("nonexistent")` | 返回 None | P0 |
| R-05 | 注销 Skill | `unregister("test-skill")` | 注销成功，工具定义移除 | P1 |

### 2.6 MCP Client

| # | 场景 | 输入 | 预期结果 | 优先级 |
|---|------|------|---------|--------|
| M-01 | 加载空配置 | 无 `MCP_SERVERS` 环境变量 | 返回空配置列表 | P0 |
| M-02 | 加载有效配置 | `MCP_SERVERS='{"filesystem": {"type": "stdio", "command": "npx"}}'` | 返回配置对象 | P0 |
| M-03 | 加载无效 JSON | `MCP_SERVERS='invalid'` | 返回空列表，不崩溃 | P1 |
| M-04 | 单例模式 | 多次调用 `get_mcp_pool()` | 返回同一实例 | P0 |
| M-05 | 启动未安装 SDK | 未安装 mcp SDK | 静默失败，不影响启动 | P1 |
| M-06 | 调用不存在的 MCP 工具 | `call_tool("nonexistent", {})` | 返回错误信息 | P1 |

### 2.7 集成测试

| # | 场景 | 输入 | 预期结果 | 优先级 |
|---|------|------|---------|--------|
| I-01 | 应用启动时注册内置 Skill | 启动应用 | 日志显示 `Built-in skills initialized` | P0 |
| I-02 | 数据库中存在内置 Skill | 查询 `skills` 表 | 包含 `web-search`、`weather`、`http-request` | P0 |
| I-03 | /api/v1/skills 列表 | GET `/api/v1/skills` | 返回内置 Skill 列表 | P0 |
| I-04 | /api/v1/tools/web-search | POST `/api/v1/tools/web-search` | 返回搜索结果 | P0 |
| I-05 | Skill 执行引擎 ReAct 循环 | 聊天中提问需要工具调用的问题 | LLM 自动调用工具并返回真实结果 | P0 |

---

## 3. 测试环境

| 环境 | 配置 |
|------|------|
| Python | 3.11+ |
| 数据库 | SQLite（测试）/ PostgreSQL（开发） |
| 外部 API | Open-Meteo（天气）、DuckDuckGo（搜索）、httpbin.org（HTTP 请求） |
| 网络 | 需要外网访问 |

---

## 4. 运行方式

```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行新增的 CLAW 相关测试
python3 -m pytest tests/skills/ tests/mcp/ -v

# 运行特定模块测试
python3 -m pytest tests/skills/test_http_request.py -v

# 生成覆盖率报告
python3 -m pytest tests/skills/ tests/mcp/ --cov=agent_forge.skills --cov=agent_forge.mcp --cov-report=html
```

---

## 5. 测试验证标准

| 标准 | 要求 |
|------|------|
| 单元测试通过率 | 100% |
| 集成测试通过率 | 100% |
| 代码覆盖率 | ≥ 80%（Skill 模块） |
| 无新增警告 | 测试运行无 DeprecationWarning |
| 性能 | 单次 Skill 调用 ≤ 30s |

---

## 6. 测试数据

### 6.1 天气查询测试城市

| 城市名 | 预期行为 |
|--------|---------|
| Beijing | 返回北京天气 |
| Shanghai | 返回上海天气 |
| Tokyo | 返回东京天气 |
| InvalidCityXYZ123 | 返回错误 |

### 6.2 HTTP 请求测试 URL

| URL | 用途 |
|-----|------|
| `https://httpbin.org/get` | GET 请求 |
| `https://httpbin.org/post` | POST 请求 |
| `https://httpbin.org/delay/10` | 超时测试 |
| `http://localhost:8000` | SSRF 防护 |
| `http://nonexistent-domain-12345.invalid` | 连接失败 |

---

## 7. 已知限制

| 限制 | 说明 |
|------|------|
| 网络依赖 | web_search、weather 测试依赖外网，离线环境会跳过 |
| MCP Server | MCP 功能测试需要安装 mcp SDK 和实际 MCP Server |
| ReAct 循环 | 需要 LLM API Key 才能测试完整的工具调用循环 |
