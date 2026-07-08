# 核心开发闭环产品需求

**日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**关联架构**：`docs/architecture/CORE-DEV-WORKFLOW.md`
**状态**：阶段实施中

> 2026-07-08 状态更新：TASK-013、TASK-014、TASK-015、TASK-016、TASK-017、TASK-018 已完成，Project / Mount / Artifact 数据底座、项目真实数据流、PipelineRun / StageState 状态机、Artifact 归档查看与上下文复用、人工确认与阶段继续、Bridge 授权文件读取已落地；TASK-019 继续推进 Delivery。

## 1. 背景

AgentForge 已经具备 Chat UI、SSE 执行可视化、Skill Engine、沙箱执行和高级设置透传能力。但这些能力仍偏向框架支撑，尚未形成面向全栈开发工程师的核心产品闭环。

路线图制定时的主要问题：

- Project / Mount / Artifact 仍停留在 PRD 和前端 mock。
- Session 未归属 Project，用户多项目上下文无法真实隔离。
- intent 和阶段配置目前主要进入 system prompt，没有运行时 PipelineRun。
- 阶段产物、人工确认和继续执行没有状态机支撑。
- TASK-007 作为静态原型已完成，但任务状态与真实核心能力容易混淆。

## 2. 产品目标

把 AgentForge 从“能聊天、能调用工具的多 Agent 框架”收敛为“围绕用户项目交付开发产物的平台”。

核心闭环：

```text
Project -> Mount -> Session -> PipelineRun -> StageState -> Artifact -> Delivery
```

## 3. 用户故事

| ID | 用户故事 | 验收信号 |
|----|----------|----------|
| CDW-01 | 作为全栈开发工程师，我希望每个对话归属于某个项目 | Session 有 project_id，切换项目后只看到该项目会话 |
| CDW-02 | 我希望上下文文件和代码库来源是我主动授权的 | ProjectMount 记录授权方式、角色和连接状态 |
| CDW-03 | 我希望需求类型真的决定执行阶段 | 发送消息后生成 PipelineRun 和 StageState |
| CDW-04 | 我希望阶段输出成为可复用产物 | 阶段完成后保存 Artifact，并能在 Chat / Project / Viewer 中查看和加入上下文 |
| CDW-05 | 我希望关键节点暂停确认 | PRD、技术选型、影响范围可触发 confirm_required |
| CDW-06 | 我希望 Agent 能逐步读我的真实代码库 | connected local Mount 内选中文件可被读取并注入 Agent 上下文 |
| CDW-07 | 我希望结果能回到我的项目 | Delivery 阶段生成 diff、写回本地或导出 |

## 4. 范围

本次路线图任务只做设计和任务拆分，不实现业务代码。

后续实现按 TASK-013 至 TASK-019 推进：

- TASK-013：Project / Mount / Artifact 数据底座。
- TASK-014：项目管理页接真实数据。
- TASK-015：PipelineRun / StageState 阶段状态机。
- TASK-016：Artifact 归档与查看。
- TASK-017：人工确认与阶段继续机制。
- TASK-018：Agent Bridge / 真实代码库读取。
- TASK-019：写回与交付闭环。

## 5. 非目标

- 不把 TASK-012 做成大而全实现任务。
- 不在数据底座阶段实现真实 Bridge。
- 不在阶段状态机阶段直接做本地文件写入。
- 不引入多人协作、权限共享、团队空间。
- 不要求一次性完成完整 8 步自动开发流水线。

## 6. 成功标准

- 任务索引明确列出 TASK-012 至 TASK-019，后续阶段不会被遗忘。
- TASK-007 的静态原型状态与真实核心能力状态分离。
- 架构文档明确 Project、Mount、PipelineRun、StageState、Artifact、Delivery 的边界。
- 每个后续任务都有独立任务文件、依赖、验收标准和产出物。
