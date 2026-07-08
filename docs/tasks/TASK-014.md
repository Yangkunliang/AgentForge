# TASK-014：项目管理页接真实数据

**状态**：todo
**优先级**：P0
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-013

**依赖状态**：TASK-013 已完成，Project / Mount / Artifact 后端模型、迁移和 API 可用于前端接入。

## 目标

将 `/projects`、`/projects/create`、`ProjectBar` 从静态 mock 改为真实 Project API 数据，让用户能创建、查看、切换项目。

## related_requirements

- CDW-01：Session 归属 Project
- CDW-02：主动授权代码库上下文

## 技术子项

- [ ] 新增前端 `project` API module
- [ ] 新增 Pinia `useProjectStore`
- [ ] `/projects` 接真实项目列表
- [ ] `/projects/create` 调用 Project/Mount API
- [ ] `ProjectBar` 从真实 store 读取当前项目
- [ ] Chat 新建 Session 时必须携带当前 project_id
- [ ] 项目切换后只展示当前项目会话
- [ ] 移除项目页面和 ProjectBar 内置 mock 数据
- [ ] 更新 `docs/tech-design/FRONTEND-ARCHITECTURE.md`

## acceptance

- [ ] 创建项目后项目列表出现真实记录
- [ ] ProjectBar 显示真实当前项目
- [ ] 切换项目后 Chat 会话范围随项目变化
- [ ] 刷新后当前项目可恢复或回到最近项目
- [ ] `cd web && npm run build` 通过

## 不做

- 不实现文件树选择器。
- 不读取本地代码文件。
- 不实现 Artifact Viewer。
