# TASK-013：Project / Mount / Artifact 数据底座

**状态**：done
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

- [x] 新增 `Project` 模型和 Alembic migration
- [x] 新增 `ProjectMount` 模型和 Alembic migration
- [x] 新增 `Artifact` 模型和 Alembic migration
- [x] `Session` 增加 `project_id`、`intent_type`、`current_pipeline_run_id`
- [x] 新增项目 CRUD API
- [x] 新增挂载 CRUD API
- [x] 新增 Artifact 基础 CRUD API
- [x] 新增默认项目迁移策略，兼容历史无 project_id 的 Session
- [x] 更新 `docs/tech-design/DATABASE.md`
- [x] 更新 `docs/tech-design/API-SPEC.md`

## acceptance

- [x] 新建 Project 后可创建归属该 Project 的 Session
- [x] Project 下可添加 local/github/upload 三类 Mount 占位
- [x] Artifact 可保存到 Project + Session 维度
- [x] 用户只能访问自己的 Project、Mount、Artifact
- [x] `uv run --extra dev pytest` 通过
- [x] FastAPI 启动无 ImportError/NameError

## 验证记录

- `uv run --extra dev pytest tests/api/test_projects.py`：5 passed
- `uv run --extra dev pytest tests/api/test_projects.py tests/api/test_route_prefixes.py tests/api/test_auth.py tests/api/test_tasks.py`：21 passed
- `uv run --extra dev pytest`：250 passed, 6 skipped, 11 xfailed
- `PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18082`：启动到 `AgentForge startup complete ✓` 后正常关闭

## 不做

- 不实现真实本地文件读取。
- 不实现 Bridge WebSocket。
- 不实现 Artifact Viewer 前端。
