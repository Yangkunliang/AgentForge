# TASK-021 UI Review：核心交互入口复盘

**日期**：2026-07-08
**任务**：TASK-021
**视角**：平台终端用户，全栈开发工程师

## 复盘结论

核心闭环已经具备 Project、Mount、Session、PipelineRun、StageState、Artifact、Delivery，但 UI 信息层级偏“数据已展示”，还不够像工程工作台。用户能看到项目、阶段和产物，却需要自己推断下一步该继续对话、确认阶段、查看产物还是进入交付。

本次不重做视觉系统，也不新增后端实体，只把现有数据组织成更明确的工作流入口。

## 发现的问题

| 区域 | 问题 | 风险 |
|------|------|------|
| Project 首页 | 已展示 Mount 和 Artifact，但没有聚合为“下一步动作” | 用户进入项目后不知道应先补连接、继续流水线还是生成第一份产物 |
| Chat 空状态 | 文案偏泛用 AI 助手，快捷入口带 emoji，和开发任务路由关系弱 | 用户把它当普通聊天框，而不是项目内开发流水线入口 |
| StagePreview | 只展示阶段 pill，缺少当前阶段摘要 | 用户需要扫完整列表才知道当前是运行中、待确认还是失败 |
| ConfirmCard | 产物名称可点，但缺少明确“查看产物并交付”入口 | 用户确认阶段前不容易发现产物详情和 Delivery 面板 |
| ArtifactCard | 只展示类型和文件类型，交付状态不可见 | 用户看不出产物是否待交付、已预览、已写回或失败 |

## 设计约束

- 保持工具型 SaaS 工作台风格，不做营销式 landing page。
- 不新增后端实体；Project 页只消费已有 Project、Mount、Session、Artifact 数据。
- 不暴露 AgentForge 开发视角，不在 UI 解释内部实现。
- 使用现有 Vue 3、Pinia、Element Plus icons，不引入新 UI 库。
- `ui-ux-pro-max` 作为 advisory 参考，仅采纳可访问性、扁平化、清晰 CTA 和任务流建议；其 landing/portfolio 建议不适用于本产品。

## 修正方案

| 区域 | 修正 |
|------|------|
| Project 首页 | 新增 `next-action` 信息条：未连接代码库、进行中流水线、已有产物、空项目分别给出不同下一步 |
| Project 首页 | 将原无行为的设置图标替换为最近产物入口，避免无效点击 |
| Chat 空状态 | 展示当前项目和代码库连接状态，快捷动作改成定位 Bug、开发新功能、迭代优化、UI 调整、架构与选型、代码 Review |
| StagePreview | 新增 `stage-preview-summary`，展示“当前：阶段名 · 状态” |
| ConfirmCard | 增加“查看产物并交付”显性入口 |
| ArtifactCard | 增加交付状态标签，并把“查看”改为“查看产物” |

## 验收覆盖

- `projects.spec.ts`
  - Project 卡片展示下一步动作和最近 Artifact。
  - 从 Project 进入 Chat 后，空状态展示当前项目与代码库连接状态。
- `human-confirmation.spec.ts`
  - ConfirmCard 展示“查看产物并交付”。
  - 点击入口进入 Artifact Viewer，且不触发确认动作。
- `pipeline-stage-state.spec.ts`
  - StagePreview 展示当前阶段和运行状态摘要。

## 剩余风险

- Project 页的“进行中流水线”只基于 Session 的 `current_pipeline_run_id` 判断，尚未展示具体 Stage 进度；后续可在 TASK-022 或新任务中补 `PipelineRun` 汇总 API。
- 本次只优化关键入口，没有重做 Artifact Viewer / Delivery 面板的整体信息架构。
- Project 详情/设置页仍不存在，代码库连接的后续管理入口需要单独拆任务。
