# TASK-008：沙箱执行层基础对接

**优先级**：P2
**状态**：已完成
**依赖**：TASK-004（Skill 插件系统）
**关联 PRD**：[INTEGRATION-CUBESANDBOX.md](../tech-design/INTEGRATION-CUBESANDBOX.md)、[SANDBOX-RESEARCH.md](../tech-design/SANDBOX-RESEARCH.md)
**关联代码**：`src/agent_forge/sandbox/`

---

## 背景

沙箱执行层的抽象接口、数据类、异常体系和运行时执行器（Docker / CubeSandbox E2B / CubeSandbox API）已完成编码。本任务完成 Phase 1（基础对接）和 Phase 2（Agent 集成），使沙箱能真实参与任务执行链路。

选型依据见 [SANDBOX-RESEARCH.md](../tech-design/SANDBOX-RESEARCH.md)：采用 Docker（可信代码）+ CubeSandbox（LLM 生成代码）分级策略。旧版 runtime `MockSandboxExecutor` 已移除，单元测试改用 `tests/sandbox/fakes.py` 中的测试专用 fake。

---

## 验收标准

- [x] 单元测试：通过测试专用 `InMemorySandboxExecutor` 覆盖本地生命周期行为，产品运行时不注册 mock provider
- [ ] CI 环境（Linux）：Docker 沙箱可正常创建、执行、销毁
- [ ] 配置注入：所有沙箱参数通过环境变量 / `CubeSandboxConfig` 读取，无硬编码
- [ ] REST API：`POST /api/v1/sandboxes/create`、`execute`、`destroy` 端点可用
- [ ] SSE 事件：沙箱生命周期事件（`sandbox_created`、`sandbox_code_completed` 等）正确推送
- [ ] TTL 回收：过期沙箱在后台被自动暂停/销毁，无泄漏

---

## Phase 1：基础对接（预计 1 周）

### 1.1 配置注入

- [x] 在 `src/agent_forge/config.py` 新增 `CubeSandboxConfig`（`CUBE_SANDBOX_ENABLED`、`CUBE_SANDBOX_URL`、`CUBE_SANDBOX_API_KEY`、`CUBE_TEMPLATE_ID`、`CUBE_SANDBOX_TIMEOUT`、`CUBE_SANDBOX_DEFAULT_PROVIDER`、`CUBE_SANDBOX_AUTO_MODE`）
- [x] 在 `.env.example` 补充沙箱相关环境变量及注释

### 1.2 工厂 / 选择器

- [x] 新增 `src/agent_forge/sandbox/factory.py`：`SandboxProviderFactory.create(provider: str) -> SandboxExecutor`，根据 `CUBE_SANDBOX_DEFAULT_PROVIDER` 返回 Docker / CubeSandboxE2B / CubeSandboxAPI

### 1.3 Skill 接入（code_executor）

- [x] 修改 `src/agent_forge/skills/code_executor.py`（或对应 Skill 实现），将 Docker 直接调用替换为 `SandboxManager.execute()`
- [x] 执行结果格式保持不变（`stdout`、`stderr`、`exit_code`、`duration_ms`）

### 1.4 REST API

- [x] 新增 `src/api/routes/sandboxes.py`，实现以下端点（参考 INTEGRATION-CUBESANDBOX.md §4.2）：
  - `POST   /api/v1/sandboxes/create`
  - `POST   /api/v1/sandboxes/{sandbox_id}/execute`
  - `POST   /api/v1/sandboxes/{sandbox_id}/files/read`
  - `POST   /api/v1/sandboxes/{sandbox_id}/files/write`
  - `POST   /api/v1/sandboxes/{sandbox_id}/pause`
  - `POST   /api/v1/sandboxes/{sandbox_id}/resume`
  - `POST   /api/v1/sandboxes/{sandbox_id}/destroy`
  - `GET    /api/v1/sandboxes`
- [x] 在 `src/api/main.py` 注册 `sandboxes_router`

### 1.5 单元测试

- [x] `tests/sandbox/test_mock_executor.py`：覆盖测试专用 `InMemorySandboxExecutor` 的 create / execute / destroy / TTL 超时 / 路径隔离
- [x] `tests/sandbox/test_manager.py`：覆盖 SandboxManager 生命周期（首次创建、续期、TTL 超时重建、destroy 后不可用）
- [x] `tests/sandbox/test_pool.py`：覆盖 SandboxPool bootstrap / acquire（命中 / 冷启动）/ release（归还 / 满池销毁）/ drain

---

## Phase 2：Agent 集成（预计 1 周）

### 2.1 Coder Agent 接入

- [x] 新增 `src/agent_forge/agents/coder.py`（或对应 Agent），代码执行改走 `SandboxManager`
- [x] 支持"生成代码 → 执行 → 读取结果 → 根据 stderr 自动修复"完整工作流

### 2.2 SSE 事件扩展

- [x] 在 `src/agent_forge/api/sse.py` 补充以下沙箱生命周期事件（参考 INTEGRATION-CUBESANDBOX.md §4.3）：
  - [x] `sandbox_created`
  - [x] `sandbox_connected`
  - [x] `sandbox_code_executing`
  - [x] `sandbox_code_completed`
  - [x] `sandbox_paused`
  - [x] `sandbox_destroyed`
  - [x] `sandbox_timeout`

### 2.3 TTL 自动回收

- [x] 新增 `src/agent_forge/sandbox/reclaimer.py`：`SandboxReclaimer` 后台协程，每 60s 扫描一次，对 TTL 超期的沙箱先 pause，超过 `PAUSE_TTL` 再 destroy
- [x] 在 `src/api/main.py` lifespan 中启动/关闭 `SandboxReclaimer`

### 2.4 降级机制

- [x] CubeSandbox 不可用（`SandboxUnavailableError`）时自动降级到 `DockerSandboxExecutor`
- [x] 降级事件写入审计日志（`sandbox_fallback_to_docker`，通过 code_executor.py 的 note 字段标记）

---

## 产出物

| 产出物 | 路径 |
|-------|------|
| 配置模型 | `src/agent_forge/config.py`（新增 `CubeSandboxConfig`） |
| 沙箱工厂 | `src/agent_forge/sandbox/factory.py` |
| 沙箱 REST API | `src/api/routes/sandboxes.py` |
| TTL 回收器 | `src/agent_forge/sandbox/reclaimer.py` |
| 单元测试 | `tests/sandbox/` |
| 环境变量说明 | `.env.example`（沙箱相关变量） |

---

## 注意事项

- macOS 本地开发不再使用 runtime mock provider；需要真实沙箱时配置 `E2B_API_KEY`，离线单元测试使用 `tests/sandbox/fakes.py`
- CubeSandbox 集成测试只在 Linux CI（配备 KVM 的 runner）上运行，通过 `pytest -m cubesandbox` 标记控制
- `DockerSandboxExecutor` 的 `files_read` / `files_write` 不支持（一次性容器），Coder Agent 需在执行结果中通过 stdout 传递文件内容，或改用 CubeSandbox
