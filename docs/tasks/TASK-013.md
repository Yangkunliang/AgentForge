# TASK-013：Project / Mount / Artifact 数据底座

**状态**：todo
**优先级**：P0
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-012

## 目标

建立 AgentForge 核心开发闭环的数据底座，让 Project、Mount、Artifact 成为真实后端实体，并让 Session 归属 Project。

## related_requirements

- CDW-01：Session 归属 Project
- CDW-02：主动授权代码库上下文
- CDW-04：阶段输出成为 Artifact

## 技术子项

- [ ] 新增 `Project` 模型和 Alembic migration
- [ ] 新增 `ProjectMount` 模型和 Alembic migration
- [ ] 新增 `Artifact` 模型和 Alembic migration
- [ ] `Session` 增加 `project_id`、`intent_type`、`current_pipeline_run_id`
- [ ] 新增项目 CRUD API
- [ ] 新增挂载 CRUD API
- [ ] 新增 Artifact 基础 CRUD API
- [ ] 新增默认项目迁移策略，兼容历史无 project_id 的 Session
- [ ] 更新 `docs/tech-design/DATABASE.md`
- [ ] 更新 `docs/tech-design/API-SPEC.md`

## acceptance

- [ ] 新建 Project 后可创建归属该 Project 的 Session
- [ ] Project 下可添加 local/github/upload 三类 Mount 占位
- [ ] Artifact 可保存到 Project + Session 维度
- [ ] 用户只能访问自己的 Project、Mount、Artifact
- [ ] `uv run --extra dev pytest` 通过
- [ ] FastAPI 启动无 ImportError/NameError

## 不做

- 不实现真实本地文件读取。
- 不实现 Bridge WebSocket。
- 不实现 Artifact Viewer 前端。
