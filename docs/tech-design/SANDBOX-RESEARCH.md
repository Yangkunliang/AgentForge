# AgentForge 沙箱机制技术调研报告

**文档状态**：已定稿
**撰写日期**：2026-06-25
**作者**：AgentForge 安全基础设施组
**关联文档**：[SECURITY.md](./SECURITY.md)、[INTEGRATION-CUBESANDBOX.md](./INTEGRATION-CUBESANDBOX.md)、[sandbox/ 包代码](../../src/agent_forge/sandbox/)

---

## 背景

AgentForge 是一个多智能体协同平台，核心使用场景之一是 Agent 自动生成代码并执行，以完成重构、测试、调试等任务。这意味着平台需要在服务器上运行来源不可信、内容不可控的代码（LLM 生成物），执行隔离是平台安全的核心基础设施。

本报告梳理了调研过程中考察的两个方案，记录各自的设计思路、能力边界与局限，以及最终选型依据，供后续维护者参考。

---

## 方案一：Docker 容器沙箱（基于 SECURITY.md §5）

### 1.1 设计思路

利用 Linux 容器技术（Namespace + Cgroup）为每次代码执行创建独立的隔离环境：

- 每次 `code_executor` Skill 调用启动一个**一次性 Docker 容器**，执行完毕后自动销毁（`remove=True`）
- 在容器级别叠加多重安全约束：网络禁用、只读文件系统、非 root 用户、内存上限
- 对低风险 Skill（天气查询、搜索等）使用更轻量的 `resource.setrlimit` 进程限制
- 文件访问依靠路径白名单（`FileAccessGuard`）+ 路径穿越检测

### 1.2 核心实现

```python
container = client.containers.run(
    image="python:3.11-slim",
    command=f"python /code/{script_name}",
    volumes={script_path: {"bind": f"/code/{script_name}", "mode": "ro"}},
    network_disabled=True,           # 禁止网络访问
    mem_limit="256m",                # 内存上限
    cpu_quota=50000,                 # CPU 50%
    read_only=True,                  # 只读文件系统
    tmpfs={"/tmp": "size=64m"},      # 临时目录（可写）
    user="nobody",                   # 非 root 用户
    security_opt=["no-new-privileges:true"],
    remove=True,                     # 执行后自动删除
    detach=True,
)
```

执行约束：

| 约束维度 | 配置值 |
|---------|-------|
| 执行超时 | 30s（wall clock） |
| 内存 | 256MB（`mem_limit`） |
| 网络 | 完全禁止（`network_disabled=True`） |
| 文件系统 | 只读挂载 + `/tmp` tmpfs |
| 进程权限 | `nobody` 用户 + `no-new-privileges` |
| ReAct 循环上限 | `SKILL_MAX_ROUNDS=5` |

### 1.3 优点

- **零额外基础设施**：Docker 在开发机和服务器上几乎普遍可用，无部署成本
- **macOS 本地开发友好**：Docker Desktop 完整支持，开发体验无障碍
- **冷启动尚可**：一次性容器冷启动约 200~500ms，对于低频代码执行可接受
- **成熟生态**：docker SDK、镜像管理、日志收集均有完善工具链
- **实现简单**：约 50 行代码即可完成基础沙箱，不引入外部服务依赖

### 1.4 局限

**核心缺陷：容器逃逸风险。**

Docker 容器共享宿主机 Linux 内核，所有容器运行在同一个内核地址空间上。当执行的代码来自 LLM 生成物（内容不可预测）或潜在恶意用户时，存在通过内核漏洞逃逸的可能：

```
容器内恶意代码
  → 利用 Kernel CVE（如 CVE-2022-0847 脏管道、eBPF 提权等）
  → 突破 Namespace 隔离
  → 拿到宿主机 root 权限
  → 读取 PostgreSQL 数据、JWT 密钥、用户代码库
```

其他局限：

- **有状态执行受限**：一次性容器不支持跨 Skill 调用的状态保持（如安装了依赖后下次调用仍需重装）
- **并发上限低**：容器调度开销随并发数增加而显著上升，单机难以支持数百并发代码执行
- **浏览器自动化不支持**：Playwright 等需要完整 OS 环境的工具在精简容器中运行困难
- **快照/回滚缺失**：无法对执行环境做快照，测试回归场景需要每次重建环境

---

## 方案二：CubeSandbox KVM MicroVM 沙箱（基于 INTEGRATION-CUBESANDBOX.md）

### 2.1 背景

[CubeSandbox](https://github.com/Yangkunliang/CubeSandbox) 是一个基于 KVM MicroVM 的高性能代码执行沙箱，由腾讯云开源，是 E2B 云服务的自部署平替实现。其核心技术特点是：通过快照克隆（CoW）实现 < 60ms 冷启动，同时每个沙箱拥有独立的 Guest OS 内核，彻底消除容器逃逸路径。

### 2.2 设计思路

在方案一的 Docker 方案之上引入第三个隔离层级，形成分级沙箱策略：

```
隔离级别 1（开发/测试）：MockSandboxExecutor
  └── 无隔离，直接 subprocess，仅用于本地开发和单元测试

隔离级别 2（可信代码）：DockerSandboxExecutor
  └── Namespace + Cgroup，适用于用户自己的项目代码

隔离级别 3（不可信代码）：CubeSandboxExecutor（E2B SDK 或 REST API）
  └── KVM 硬件级隔离，每个沙箱独立内核，适用于 LLM 生成代码
```

三个执行器共同实现 `SandboxExecutor` Protocol，上层（Skill / Agent）完全不感知底层差异：

```python
# 上层调用方式完全统一
async with SandboxManager(executor, ttl_seconds=300) as mgr:
    result = await mgr.execute("print('hello')")
```

### 2.3 隔离机制原理

Docker 方案与 CubeSandbox 方案的根本差异在于内核共享模式：

```
Docker（共享内核）：
┌──────────────────────────────────────────┐
│  宿主机（共享 Linux 内核）                  │
│  ┌────────┐  ┌────────┐  ┌────────┐      │
│  │ 容器 1 │  │ 容器 2 │  │ 容器 N │      │
│  └────────┘  └────────┘  └────────┘      │
│        ↑ 内核漏洞可穿透所有容器             │
└──────────────────────────────────────────┘

CubeSandbox（独立内核）：
┌──────────────────────────────────────────┐
│  宿主机（KVM 虚拟化层）                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ VM 沙箱1 │  │ VM 沙箱2 │  │ VM 沙箱N │ │
│  │ 独立内核  │  │ 独立内核  │  │ 独立内核  │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│        ↑ 内核漏洞只影响当前沙箱，无法逃逸     │
└──────────────────────────────────────────┘
```

### 2.4 优点

- **内核级隔离**：每个沙箱拥有独立 Guest OS 内核，彻底消除容器逃逸风险，即使代码利用内核 CVE，影响范围也被限制在当前沙箱内
- **冷启动极快**：基于快照克隆 + CoW 内存复用，冷启动 < 60ms，比 Docker 容器（200ms+）快 3~5 倍；配合热沙箱池可降至接近 0ms
- **高密度并发**：单沙箱内存开销 < 5MB，单机可支持数千并发实例
- **有状态持久执行**：沙箱生命周期内可跨多次 Skill 调用，支持"安装依赖 → 执行 → 读取结果"的完整工作流
- **快照与回滚**：支持在特定状态创建快照，测试回归可直接从快照恢复，无需重建环境
- **完整 OS 环境**：支持 Playwright、Chrome headless 等需要完整桌面环境的工具
- **E2B SDK 兼容**：与 E2B 云服务 API 完全兼容，仅需修改两个环境变量即可在自部署和 E2B 云之间切换；也支持直接调用 REST API 做精细控制
- **降级机制完善**：CubeSandbox 不可用时自动降级到 Docker 沙箱，保证业务连续性

### 2.5 局限

- **依赖 KVM**：需要宿主机支持硬件虚拟化，无法在 Docker 容器内或 WSL 中部署；macOS 本地开发无法直接运行真实 CubeSandbox
- **仅支持 Linux**：CubeSandbox 服务端仅支持 Ubuntu 22.04/24.04 或 OpenCloudOS 9（需 XFS 文件系统）
- **运维成本**：需要维护独立的 CubeSandbox 集群（CubeAPI、CubeMaster、Cubelet、CubeProxy、CubeVS 等组件）
- **磁盘消耗**：CoW 快照会消耗额外磁盘空间，需定期清理；生产环境建议磁盘 ≥ 200GB
- **模板管理**：执行环境以"模板"为单位管理，需预先构建包含所需运行时（Python、Node 等）的模板镜像

---

## 方案对比

### 3.1 核心维度对比表

| 对比维度 | 方案一：Docker 容器 | 方案二：CubeSandbox KVM |
|---------|-------------------|----------------------|
| **隔离机制** | Namespace + Cgroup（容器级） | KVM MicroVM（内核级） |
| **内核共享** | ⚠️ 共享宿主机内核 | ✅ 每个沙箱独立内核 |
| **容器逃逸风险** | ⚠️ 存在（内核 CVE 可穿透） | ✅ 不存在（独立内核隔离） |
| **冷启动延迟** | ~200ms（容器创建） | < 60ms（快照克隆） |
| **热沙箱延迟** | 不支持（一次性容器） | ~0ms（池化预热） |
| **并发上限（单机）** | 数十个（调度开销大） | 数千个（< 5MB/沙箱） |
| **有状态执行** | ❌ 不支持（一次性销毁） | ✅ 支持（TTL 内持久） |
| **快照 / 回滚** | ❌ 不支持 | ✅ 支持 |
| **浏览器自动化** | ⚠️ 受限（精简镜像） | ✅ 支持（完整 OS） |
| **macOS 本地开发** | ✅ Docker Desktop 直接支持 | ⚠️ 需配合 MockSandboxExecutor |
| **部署复杂度** | ✅ 低（Docker 普遍可用） | ⚠️ 中（需独立服务集群） |
| **基础设施依赖** | Docker daemon | CubeSandbox 集群 + KVM |
| **运维成本** | ✅ 低 | ⚠️ 中（多组件管理） |
| **外部服务依赖** | ❌ 无 | ⚠️ 有（CubeSandbox 服务） |
| **E2B 云服务兼容** | ❌ 不适用 | ✅ API 完全兼容，可托管切换 |
| **适合的代码类型** | 可信代码（用户自有项目代码） | 不可信代码（LLM 生成物、外部 Skill） |
| **适合的规模** | 小规模（< 50 并发） | 中大规模（100~1000+ 并发） |

### 3.2 安全能力对比

| 安全能力 | 方案一：Docker | 方案二：CubeSandbox |
|---------|--------------|-------------------|
| 进程隔离 | ✅ | ✅ |
| 文件系统隔离 | ✅（只读挂载） | ✅（CoW 层） |
| 网络隔离 | ✅（`network_disabled`） | ✅（CubeVS eBPF 过滤） |
| 内存限制 | ✅（`mem_limit`） | ✅（模板规格约束） |
| CPU 限制 | ✅（`cpu_quota`） | ✅（模板规格约束） |
| 内核漏洞防护 | ❌ 无法防御（共享内核） | ✅ 独立内核，漏洞不跨沙箱 |
| 多租户隔离 | ⚠️ 容器层面（存在逃逸路径） | ✅ VM 层面（硬件级） |
| 执行环境审计 | ⚠️ 基础日志 | ✅ 快照审计 + 完整日志 |

### 3.3 适用场景映射

| 执行场景 | 推荐方案 | 原因 |
|---------|---------|------|
| 用户自己的项目代码（可信） | 方案一：Docker | 足够安全，部署简单 |
| LLM 生成的代码（不可信） | 方案二：CubeSandbox | 内核级隔离，防逃逸 |
| 外部 Skill / 社区插件 | 方案二：CubeSandbox | 来源不可信，需最强隔离 |
| 并发测试 / 回归测试 | 方案二：CubeSandbox | 快照回滚 + 高并发 |
| 浏览器自动化（Playwright） | 方案二：CubeSandbox | 需完整 OS 环境 |
| 本地开发 / 单元测试 | Mock（两方案均支持） | MockSandboxExecutor |

---

## 选型决策

### 4.1 结论

**采用方案二（CubeSandbox KVM MicroVM）作为不可信代码执行的主要沙箱方案，方案一（Docker）保留用于可信代码执行场景，两者并存形成分级隔离策略。**

### 4.2 决策依据

**安全是决定性因素。** AgentForge 的核心产品承诺是"Agent 帮用户写代码并执行"，这意味着平台必须在服务器上运行 LLM 生成的任意代码。这类代码的特点是：

- 内容由 LLM 生成，可能产生意料之外的系统调用
- 可能被用户故意注入恶意代码（通过 Prompt 注入路径）
- 平台无法在执行前对代码做完整的静态分析

在这种场景下，Docker 容器的"共享内核"架构存在根本性的安全边界缺陷。一个 Kernel CVE（近年来平均每年发现数十个）就可以让隔离完全失效。CubeSandbox 的独立内核架构从根本上消除了这条攻击路径。

**性能反而是额外收益。** CubeSandbox 不仅安全性更高，冷启动（< 60ms vs 200ms+）和并发密度（数千 vs 数十）也均优于 Docker 方案，不存在"为安全性牺牲性能"的权衡。

**开发体验问题有完善的规避方案。** macOS 无法运行真实 CubeSandbox 的问题，通过 `MockSandboxExecutor` 完全解决：本地开发和单元测试走 Mock，CI/CD 和集成测试在 Linux KVM 主机上运行真实沙箱。三个执行器共享同一套 `SandboxExecutor` Protocol，切换完全透明。

**降级机制保证业务连续性。** CubeSandbox 服务异常时自动降级到 Docker 沙箱，不影响核心功能。

### 4.3 不选方案一作为主方案的原因

| 风险点 | 具体说明 |
|-------|---------|
| 内核漏洞可穿透 | 历史真实案例：CVE-2022-0847（脏管道）可从容器内获取宿主机任意文件读写权限 |
| 攻击成本低 | 公开的容器逃逸 PoC 极多，门槛低，不需要 0day |
| 平台责任风险 | 若因容器逃逸导致其他用户数据泄露，平台需承担连带责任 |
| 无法支持有状态工作流 | Agent 执行"安装依赖 → 写文件 → 运行测试"的完整工作流时，一次性容器需要每步重建，效率极低 |

### 4.4 两方案共存的架构

最终不是"选一个、放弃另一个"，而是两方案各司其职：

```
执行请求
    │
    ▼ auto 模式路由（CUBE_SANDBOX_AUTO_MODE=true）
    │
    ├── code_execution / shell / testing / 外部 Skill
    │       └──→ CubeSandboxExecutor（KVM 隔离）
    │
    └── 用户自有项目代码（可信场景）
            └──→ DockerSandboxExecutor（容器隔离）
```

本地开发：

```
CUBE_SANDBOX_DEFAULT_PROVIDER=mock
    └──→ MockSandboxExecutor（无隔离，subprocess，仅开发用）
```

---

## 实施现状

| 组件 | 状态 | 位置 |
|------|------|------|
| `SandboxExecutor` Protocol + 数据类 + 异常 | ✅ 已实现 | `src/agent_forge/sandbox/base.py` |
| `SandboxManager`（生命周期 + TTL） | ✅ 已实现 | `src/agent_forge/sandbox/manager.py` |
| `SandboxPool`（热沙箱池 + cleanup + 冷启动降级） | ✅ 已实现 | `src/agent_forge/sandbox/pool.py` |
| `SandboxReclaimer`（TTL 后台扫描 + 自动回收） | ✅ 已实现 | `src/agent_forge/sandbox/reclaimer.py` |
| `MockSandboxExecutor`（本地开发） | ✅ 已实现 | `src/agent_forge/sandbox/mock.py` |
| `DockerSandboxExecutor`（方案一） | ✅ 已实现 | `src/agent_forge/sandbox/docker.py` |
| `CubeSandboxE2BExecutor`（E2B SDK 路径） | ✅ 已实现 | `src/agent_forge/sandbox/cubesandbox/e2b.py` |
| `CubeSandboxAPIExecutor`（REST API 路径） | ✅ 已实现 | `src/agent_forge/sandbox/cubesandbox/api.py` |
| `CubeSandboxConfig` + 环境变量 | ⬜ 待实现（Phase 1） | `src/agent_forge/config.py` |
| 沙箱管理 REST API | ⬜ 待实现（Phase 1） | `src/api/routes/sandboxes.py` |
| Coder Agent 集成 | ⬜ 待实现（Phase 2） | `src/agent_forge/agents/` |
| 前端沙箱状态 UI | ⬜ 待实现（Phase 3） | `web/src/` |

详细实施计划见 [INTEGRATION-CUBESANDBOX.md §12](./INTEGRATION-CUBESANDBOX.md)。

---

## 参考资料

- [CubeSandbox GitHub](https://github.com/Yangkunliang/CubeSandbox)
- [E2B 官方文档](https://e2b.dev/docs)
- [SECURITY.md §5 — Skill 沙箱（方案一详细设计）](./SECURITY.md)
- [INTEGRATION-CUBESANDBOX.md（方案二详细设计）](./INTEGRATION-CUBESANDBOX.md)
- CVE-2022-0847 Dirty Pipe：容器逃逸真实案例参考
- [gVisor](https://gvisor.dev/)、[Kata Containers](https://katacontainers.io/)：其他 VM 级沙箱参考，未纳入本期调研
