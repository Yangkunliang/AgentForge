# TASK-016：Artifact 产物归档与查看

**状态**：done
**优先级**：P1
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-015

**依赖状态**：TASK-015 已完成，PipelineRun / StageState / StageRuntime 可作为 Artifact 归档触发点。

## 目标

让每个阶段输出保存为可查看、可复用、可作为上下文的 Artifact，而不是只存在于聊天消息中。

## related_requirements

- CDW-04：阶段输出成为 Artifact

## 技术子项

- [x] StageRuntime 在阶段完成后创建 Artifact
- [x] Artifact 支持 prd / architecture / api_spec / code / test / report / diff 类型
- [x] 新增 Artifact Viewer 页面
- [x] Chat 消息区展示 ArtifactCard
- [x] Artifact 可添加为下一次对话上下文
- [x] Project 详情页展示 Artifact 列表
- [x] 新增 `artifact_created` SSE 事件
- [x] 更新前端类型和 API module

## acceptance

- [x] 阶段完成后生成 Artifact 记录
- [x] 用户可从 Chat 和 Project 查看 Artifact
- [x] Markdown / code / text 类型至少能正确渲染
- [x] Artifact 可作为 context chip 引用
- [x] `cd web && npm run build` 通过
- [x] `uv run --extra dev pytest` 通过

## 不做

- 不写回本地文件。
- 不做对象存储。
- 不做多人共享权限。
