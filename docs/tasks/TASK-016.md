# TASK-016：Artifact 产物归档与查看

**状态**：todo
**优先级**：P1
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-015

## 目标

让每个阶段输出保存为可查看、可复用、可作为上下文的 Artifact，而不是只存在于聊天消息中。

## related_requirements

- CDW-04：阶段输出成为 Artifact

## 技术子项

- [ ] StageRuntime 在阶段完成后创建 Artifact
- [ ] Artifact 支持 prd / architecture / api_spec / code / test / report / diff 类型
- [ ] 新增 Artifact Viewer 页面
- [ ] Chat 消息区展示 ArtifactCard
- [ ] Artifact 可添加为下一次对话上下文
- [ ] Project 详情页展示 Artifact 列表
- [ ] 新增 `artifact_created` SSE 事件
- [ ] 更新前端类型和 API module

## acceptance

- [ ] 阶段完成后生成 Artifact 记录
- [ ] 用户可从 Chat 和 Project 查看 Artifact
- [ ] Markdown / code / text 类型至少能正确渲染
- [ ] Artifact 可作为 context chip 引用
- [ ] `cd web && npm run build` 通过
- [ ] `uv run --extra dev pytest` 通过

## 不做

- 不写回本地文件。
- 不做对象存储。
- 不做多人共享权限。
