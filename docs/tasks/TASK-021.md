# TASK-021：核心交互设计复盘与关键入口优化

**状态**：todo
**优先级**：P1
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-STRENGTHENING
**依赖**：TASK-020

## 目标

从终端用户“全栈开发工程师”的视角复盘核心闭环交互，让 Project、Chat、Stage、Artifact、Delivery 的下一步动作更清楚，减少用户在页面之间找入口的成本。

## related_requirements

- CDW-01：Project 是一等容器
- CDW-04：阶段输出可查看、复用和追溯
- CDW-05：关键节点人工确认
- CDW-09：核心工作流下一步动作必须可见

## 技术子项

- [ ] 新增 `docs/iterations/2026-07-08-core-strengthening/UI-REVIEW.md`
- [ ] 复盘 Project 首页、Chat、StagePreview、Artifact Viewer、Delivery 面板的信息层级
- [ ] 阶段完成卡片明确展示 Artifact、确认和交付入口
- [ ] Project 首页展示当前进行中的 PipelineRun、最近 Artifact 和 Mount 健康状态
- [ ] Chat 空状态根据 Project/Mount/Session 状态给出面向开发任务的快捷动作
- [ ] 补充浏览器 E2E 验证关键入口可达

## acceptance

- [ ] 用户从 Project 进入后能看到当前项目的下一步动作
- [ ] 用户完成阶段后不用猜测 Artifact 和 Delivery 在哪里
- [ ] 用户在 Chat 中能理解当前阶段是否等待确认、已完成或可交付
- [ ] UI 文案不解释内部实现，不暴露 AgentForge 开发视角

## 不做

- 不新增后端实体。
- 不做营销式 landing page。
- 不重做整体视觉系统。
