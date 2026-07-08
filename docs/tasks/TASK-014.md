# TASK-014：项目管理页接真实数据

**状态**：done
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

- [x] 新增前端 `project` API module
- [x] 新增 Pinia `useProjectStore`
- [x] `/projects` 接真实项目列表
- [x] `/projects/create` 调用 Project/Mount API
- [x] `ProjectBar` 从真实 store 读取当前项目
- [x] Chat 新建 Session 时必须携带当前 project_id
- [x] 项目切换后只展示当前项目会话
- [x] 移除项目页面和 ProjectBar 内置 mock 数据
- [x] 更新 `docs/tech-design/FRONTEND-ARCHITECTURE.md`

## acceptance

- [x] 创建项目后项目列表出现真实记录
- [x] ProjectBar 显示真实当前项目
- [x] 切换项目后 Chat 会话范围随项目变化
- [x] 刷新后当前项目可恢复或回到最近项目
- [x] `cd web && npm run build` 通过

## 产出物

- 新增 `web/src/api/modules/projects.ts`，封装 Project、Project Session、Mount API。
- 新增 `web/src/stores/project.ts`，维护项目列表、当前项目、本地恢复和 Mount 缓存。
- `/projects` 改为读取真实 Project API，并展示主 Mount 连接状态。
- `/projects/create` 在完成向导时创建 Project 和 primary Mount。
- `ProjectBar` 改为读取 `useProjectStore`，切换项目后刷新当前项目会话。
- `SessionStore` 新建/拉取会话时优先使用当前 `project_id`。
- 新增 `web/e2e/projects.spec.ts` 覆盖项目列表、创建、切换、刷新恢复和项目会话作用域。

## 验证

- `npm run test:e2e -- projects.spec.ts`
- `npm run build`

## 不做

- 不实现文件树选择器。
- 不读取本地代码文件。
- 不实现 Artifact Viewer。
