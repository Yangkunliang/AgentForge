# AgentForge 核心开发闭环

本文档定义 AgentForge 面向全栈开发工程师的核心产品闭环。它用于统一后续 TASK-012 至 TASK-019 的实现边界，避免项目管理、对话体验、产物归档和代码库访问分散推进。

## 1. 核心闭环

AgentForge 的核心功能不是单纯聊天，也不是单纯多 Agent 编排，而是围绕用户自己的项目完成开发交付：

```text
Project -> Mount -> Session -> PipelineRun -> StageState -> Artifact -> Delivery
```

| 概念 | 定义 | 当前状态 | 后续任务 |
|------|------|----------|----------|
| Project | 用户的一个产品或代码库，是会话和产物的归属容器 | 后端模型、API、前端真实数据流、项目产物列表与 Bridge 状态已实现 | 已接 Delivery |
| Mount | 用户主动授权的代码库访问入口，本地目录、GitHub 或上传文件 | connected local Mount 已支持授权 root 内目录列表、只读文件读取和确认写回；GitHub OAuth Mount 已支持 state 校验、服务端加密凭据和 connected GitHub Mount 创建；TASK-022 已完成 GitHub / upload 授权边界设计 | TASK-026 扩展 Upload Mount |
| Session | 归属于 Project 的一次对话或开发任务上下文 | 已支持 `project_id`、`intent_type`、`current_pipeline_run_id`，消息可带关联 Artifact，Chat 可显示确认卡片和授权文件上下文 | 可继续增强多阶段自动推进 |
| PipelineRun | 一次需求按 intent 生成的阶段化执行计划 | 模型、API、chat 首次创建、StageRuntime、Artifact 输出、人工确认暂停与授权文件内容注入已实现 | 可继续增强 Delivery 自动编排 |
| StageState | PipelineRun 内每个阶段的状态、跳过、确认和输出 | 已支持 pending/running/waiting_confirmation/completed/skipped/failed、确认反馈、StagePreview 后端渲染与真实上下文读取 | 可继续增强交付事件 |
| Artifact | 阶段输出，如 PRD、架构、代码、测试报告 | StageRuntime 自动归档，Chat / Project / Viewer 可查看并加入上下文；Viewer 可预览 diff 并交付 | 已接 Delivery |
| Delivery | 将产物写回本地项目、生成 PR、导出 zip 或交付报告 | 已支持本地 Artifact diff preview、`confirm_write` 后写回授权 Mount、写前备份、交付报告和 Markdown 导出；已支持 GitHub PR Delivery preview/apply、base sha 二次校验、branch/commit/PR 创建、失败报告和审计 | TASK-025 扩展 zip Delivery |

## 2. 用户路径

MVP 用户路径按以下顺序落地：

1. 用户创建 Project，填写名称、描述和技术栈。
2. 用户在创建向导中添加 primary Mount；也可以通过 `agentforge mount <path>` 创建 connected local Mount，或通过 GitHub OAuth 授权远程仓库 Mount。
3. 用户从 Project 进入 Chat，创建归属于 Project 的 Session；刷新后当前项目从本地选择状态恢复。
4. 用户选择需求类型，或由规则分类得到 intent。
5. 系统创建 PipelineRun，并根据 intent 初始化 StageState。
6. 用户可从 connected local Mount 选择文件作为上下文；后端在执行前读取授权 root 内的真实文件内容并注入 Agent。
7. Agent 执行当前阶段，阶段完成后保存 Artifact。
8. 如阶段需要人工确认，系统进入 `waiting_confirmation`，生成 Artifact 并在 Chat 显示 ConfirmCard。
9. 用户确认后进入下一阶段；用户提出修改意见后回到同阶段重新执行；用户取消后 run 进入 `cancelled`。
10. 用户在 Artifact Viewer 中选择本地写回或 GitHub PR Delivery：本地模式预览 unified diff 后确认写回授权目录；GitHub 模式预览远程 diff 和 base sha 后确认创建 branch、commit 与 PR，并导出 Markdown Delivery report。

## 3. 设计原则

- Project 是一等公民。任何 Session、PipelineRun、Artifact 都必须能追溯到 Project。
- Mount 是用户主动授权，不自动扫描用户目录。
- Intent 不只是 prompt 文案，必须生成可检查的 PipelineRun。
- StageState 是状态机，不是纯 UI pill。
- Artifact 是平台产物，不应该只散落在聊天消息里。
- 人工确认是流程节点，不是普通按钮。
- Bridge 读取必须始终受 Mount 授权范围约束；Delivery 仍需复用 Mount 边界。
- GitHub OAuth token 只允许服务端加密存储，ProjectMount、审计日志、前端响应和 Delivery report 不得包含明文 token。
- Delivery 预览和写入之间必须保持可验证的一致性；若本地目标文件或远程 base ref 已变化，默认拒绝写入并生成失败报告。
- 写回用户项目、创建远程 PR、导出 zip 的成功、拒绝、冲突和失败都必须进入审计日志，且审计 details 不记录 Artifact 内容、OAuth token 或上传文件正文。
- Upload Mount 只代表用户主动上传的文件集合，不得反推或访问用户本地路径，也不得作为写回目标。

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
              -> TASK-020 服务端可信交付巩固
                -> TASK-021 核心交互设计复盘
                  -> TASK-022 交付能力扩展设计
                    -> TASK-023 GitHub OAuth Mount
                      -> TASK-024 GitHub PR Delivery
                    -> TASK-025 zip Delivery Package
                    -> TASK-026 Upload Mount
```

## 5. MVP 非目标

- 不做多人协作。
- 不做完整 GitHub App PR 流程；当前远程交付基于用户显式授权的 GitHub OAuth Mount 创建单仓库 PR，不自动 merge。
- 不在 TASK-013 中实现真实本地文件读取；TASK-018 已实现用户选中文件的只读读取。
- 不要求 Agent 自动完成完整 8 步流水线；当前阶段状态机已支持运行态推进、产物归档与人工确认暂停。
- 不把用户选择的文件路径当作已读取内容，真实读取必须经过 Mount/Bridge 授权。
- 不支持跨 repo 批量 PR；远程写入必须先 preview、再确认，并拒绝已撤销凭据。

## 6. 完成定义

核心闭环完成时，用户应能完成以下端到端路径：

```text
创建项目 -> 创建会话 -> 选择需求类型 -> 生成阶段计划
-> 完成一个阶段 -> 保存产物 -> 人工确认 -> 进入下一阶段
-> 查看产物 -> 将结果交付到本地、GitHub PR 或导出
```

Delivery 不能绕过用户确认；只有在用户明确确认写入后，Artifact 内容才能写回授权 Mount。
