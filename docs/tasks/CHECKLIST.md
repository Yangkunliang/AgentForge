# AgentForge 实现任务索引

> `CHECKLIST.md` 只做任务索引和进度总览；每个任务的需求关联、技术子项、验收标准和产出物写入独立 `TASK-NNN.md` 文件。

## 任务拆分原则

产品需求先映射到用户故事，再拆成实现任务：

```text
PRODUCT-REQUIREMENTS / PRD
  -> 用户故事 US-N
    -> TASK-NNN
      -> 技术子项 checklist
      -> 验收标准
      -> 产出物
```

执行时按任务粒度推进：完成 1 个 `TASK-NNN.md` 中的可验收任务后，更新该任务状态并单独 commit。

## 用户故事覆盖矩阵

| 用户故事 | 产品目标 | 覆盖任务 |
|---|---|---|
| US-1 | 输入自然语言需求，系统自动拆解并分派给合适 Agent | [TASK-002](TASK-002.md)、[TASK-003](TASK-003.md)、[TASK-005](TASK-005.md)、[TASK-006](TASK-006.md) |
| US-2 | Agent 自动完成产品设计、UI 设计、任务拆解 | [TASK-002](TASK-002.md)、[TASK-003](TASK-003.md)、[TASK-005](TASK-005.md)、[TASK-006](TASK-006.md) |
| US-3 | 快速导入新的 Skill 插件 | [TASK-004](TASK-004.md)、[TASK-005](TASK-005.md) |
| US-4 | 导出训练数据，优化模型和 Agent 路由 | [TASK-004](TASK-004.md)、[TASK-005](TASK-005.md) |
| US-5 | 查看安全 API 调用记录，用于审计和合规 | [TASK-001](TASK-001.md)、[TASK-003](TASK-003.md)、[TASK-004](TASK-004.md)、[TASK-005](TASK-005.md) |

## 任务列表

| 状态 | 任务 | 优先级 | 关联需求 | 依赖 | 说明 |
|---|---|---|---|---|---|
| [x] | [TASK-001：项目基础设施 & 认证系统](TASK-001.md) | P1 | US-5，支撑全部 US | 无 | 建立后端工程、数据库、认证、限流和 trace 基础 |
| [x] | [TASK-002：任务管理 & Agent 管理 API](TASK-002.md) | P1 | US-1、US-2 | TASK-001 | 提供任务和 Agent 的基础 API 入口 |
| [x] | [TASK-003：Harness 核心 + RabbitMQ + SSE](TASK-003.md) | P2 | US-1、US-2、US-5 | TASK-001、TASK-002 | 落地多 Agent 编排、Contract Net、实时流式过程 |
| [x] | [TASK-004：Skill 插件系统 & 辅助 API](TASK-004.md) | P2 | US-3、US-4、US-5 | TASK-001、TASK-003 | 实现 Skill 安装、Dashboard、成本、导出、Webhook |
| [x] | [TASK-005：前端工作台 & UI/UX 体验](TASK-005.md) | P3 | US-1、US-2、US-3、US-4、US-5 | TASK-001、TASK-002、TASK-003、TASK-004 | 建立 Vue 3 前端工作台、SSE 可视化、权限页面和管理界面 |
| [x] | [TASK-006：面向用户的对话工作台（Chat UI）](TASK-006.md) | P2 | US-1、US-2 | TASK-001、TASK-002、TASK-003 | 用户侧对话界面：会话列表、流式气泡、SSE 接入，多 Agent 细节对用户透明 |
| [x] | [TASK-007：全栈 Agent 交互体验 — 静态页面](TASK-007.md) | P2 | US-01～US-05（PRD-全栈Agent交互体验）| TASK-005、TASK-006 | 项目管理页 + Agent 对话页新交互层，纯静态 mock，验证体验后再接后端 |
| [ ] | [TASK-008：沙箱执行层基础对接](TASK-008.md) | P2 | US-3、US-5 | TASK-004 | 完成 sandbox 包配置注入、REST API、Coder Agent 集成、TTL 回收机制（Phase 1+2） |

## 执行顺序

```text
TASK-001
  -> TASK-002
    -> TASK-003
      -> TASK-004
        -> TASK-005
      -> TASK-006  （可与 TASK-004 并行，依赖 TASK-003 SSE 稳定后启动）
```

前端任务 `TASK-005` 可以在 API 合同稳定后提前进行 UI 设计，但正式联调依赖后端核心 API 和 SSE 事件格式稳定。

## 进度更新规则

- 任务细节只在对应 `TASK-NNN.md` 中维护。
- `CHECKLIST.md` 只更新任务级状态、依赖关系和覆盖矩阵。
- 完成一个任务文件中的 checklist item 后，先在任务文件中勾选，再提交。
- 完成整个任务后，再在本文件中把对应任务状态改为 `[x]`。
- 如果新增任务，必须同时更新用户故事覆盖矩阵和任务列表。
