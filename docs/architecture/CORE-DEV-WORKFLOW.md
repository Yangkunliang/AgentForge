# AgentForge 核心开发闭环

本文档定义 AgentForge 面向全栈开发工程师的核心产品闭环。它用于统一后续 TASK-012 至 TASK-019 的实现边界，避免项目管理、对话体验、产物归档和代码库访问分散推进。

## 1. 核心闭环

AgentForge 的核心功能不是单纯聊天，也不是单纯多 Agent 编排，而是围绕用户自己的项目完成开发交付：

```text
Project -> Mount -> Session -> PipelineRun -> StageState -> Artifact -> Delivery
```

| 概念 | 定义 | 当前状态 | 后续任务 |
|------|------|----------|----------|
| Project | 用户的一个产品或代码库，是会话和产物的归属容器 | 后端模型、API 与前端真实数据流已实现 | TASK-015 接 PipelineRun |
| Mount | 用户主动授权的代码库访问入口，本地目录、GitHub 或上传文件 | 后端占位模型与 API 已实现 | TASK-018 接真实 Bridge |
| Session | 归属于 Project 的一次对话或开发任务上下文 | 已支持 `project_id`、`intent_type`、默认项目兼容 | TASK-015 接 PipelineRun |
| PipelineRun | 一次需求按 intent 生成的阶段化执行计划 | 尚无运行时实体 | TASK-015 |
| StageState | PipelineRun 内每个阶段的状态、跳过、确认和输出 | 仅前端展示 | TASK-015、TASK-017 |
| Artifact | 阶段输出，如 PRD、架构、代码、测试报告 | 后端基础模型与 CRUD API 已实现 | TASK-016 接查看与复用 |
| Delivery | 将产物写回本地项目、生成 diff 或 PR | 尚无闭环 | TASK-019 |

## 2. 用户路径

MVP 用户路径按以下顺序落地：

1. 用户创建 Project，填写名称、描述和技术栈。
2. 用户在创建向导中添加 primary Mount。MVP 允许手动路径、GitHub 仓库 URL 或上传文件占位，真实 Bridge 在后续接入。
3. 用户从 Project 进入 Chat，创建归属于 Project 的 Session；刷新后当前项目从本地选择状态恢复。
4. 用户选择需求类型，或由规则分类得到 intent。
5. 系统创建 PipelineRun，并根据 intent 初始化 StageState。
6. Agent 执行当前阶段，阶段完成后保存 Artifact。
7. 如阶段需要人工确认，系统暂停并等待用户确认。
8. 用户确认后进入下一阶段，直到生成可交付结果。
9. 后续 Delivery 阶段把产物写回本地目录、生成 diff、测试报告或 PR。

## 3. 设计原则

- Project 是一等公民。任何 Session、PipelineRun、Artifact 都必须能追溯到 Project。
- Mount 是用户主动授权，不自动扫描用户目录。
- Intent 不只是 prompt 文案，必须生成可检查的 PipelineRun。
- StageState 是状态机，不是纯 UI pill。
- Artifact 是平台产物，不应该只散落在聊天消息里。
- 人工确认是流程节点，不是普通按钮。
- Bridge 和真实代码读取可以延后，但数据模型必须预留 Mount 与 Delivery 边界。

## 4. 分阶段落地

```text
TASK-012 路线图和状态纠偏
  -> TASK-013 Project / Mount / Artifact 数据底座
    -> TASK-014 项目管理页接真实数据
    -> TASK-015 PipelineRun / StageState 阶段状态机
      -> TASK-016 Artifact 归档与查看
      -> TASK-017 人工确认与阶段继续
        -> TASK-018 Agent Bridge 和真实代码库读取
          -> TASK-019 写回与交付闭环
```

## 5. MVP 非目标

- 不做多人协作。
- 不做完整 GitHub App PR 流程，TASK-019 只保留可扩展接口。
- 不在 TASK-013 中实现真实本地文件读取。
- 不要求 Agent 自动完成完整 8 步流水线，阶段状态机先支持人工确认和产物归档。
- 不把用户选择的文件路径当作已读取内容，真实读取必须经过 Mount/Bridge 授权。

## 6. 完成定义

核心闭环完成时，用户应能完成以下端到端路径：

```text
创建项目 -> 创建会话 -> 选择需求类型 -> 生成阶段计划
-> 完成一个阶段 -> 保存产物 -> 人工确认 -> 进入下一阶段
-> 查看产物 -> 将结果交付到本地或导出
```

只要 PipelineRun、StageState、确认机制或 Delivery 仍是 mock，就不能把核心开发闭环标记为完成。
