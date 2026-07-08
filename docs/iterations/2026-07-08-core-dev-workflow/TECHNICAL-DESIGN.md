# 核心开发闭环技术设计

**日期**：2026-07-08
**关联架构**：`docs/architecture/CORE-DEV-WORKFLOW.md`
**状态**：方案设计

## 1. 总体架构

核心闭环新增一条产品运行时主链路：

```text
ProjectService
  -> SessionService
    -> PipelineService
      -> StageRuntime
        -> ArtifactService
          -> DeliveryService
```

已有 Chat、Skill Engine、SSE、Sandbox 不替换，只作为 StageRuntime 的执行能力。

## 2. 数据模型规划

### 2.1 Project

```text
projects
- id
- user_id
- name
- description
- tech_tags
- status
- created_at
- updated_at
```

约束：

- 同一用户下项目名称允许重复，但 UI 应提示避免混淆。
- Project 删除采用软删除或级联前确认，避免误删会话和产物。

### 2.2 ProjectMount

```text
project_mounts
- id
- project_id
- mount_type: local | github | upload
- display_name
- locator
- role: primary | reference | docs
- status: connected | disconnected | pending | error
- metadata
- created_at
- updated_at
```

`locator` 可表示本地路径、GitHub repo 或上传文件组 ID。真实本地读取在 TASK-018 接入 Bridge。

### 2.3 Session 扩展

```text
sessions
- project_id
- intent_type
- current_pipeline_run_id
```

规则：

- 新建 Session 必须指定 project_id。
- 历史无项目 Session 通过默认 Project 或迁移脚本兜底。

### 2.4 PipelineRun / StageState

```text
pipeline_runs
- id
- project_id
- session_id
- intent_type
- status: planned | running | waiting_confirmation | completed | failed | cancelled
- current_stage_id
- created_at
- updated_at

pipeline_stage_states
- id
- pipeline_run_id
- stage_id
- stage_name
- order_index
- required
- status: pending | running | waiting_confirmation | completed | skipped | failed
- skip_reason
- confirmation_required
- started_at
- completed_at
```

阶段配置由 `usePipeline.ts` 与后端共享一份语义表。后端是最终状态源，前端只负责展示和用户操作。

### 2.5 Artifact

```text
artifacts
- id
- project_id
- session_id
- pipeline_run_id
- stage_state_id
- artifact_type: prd | architecture | api_spec | code | test | report | diff
- name
- content
- file_type
- source_message_id
- metadata
- created_at
```

MVP 存数据库 content 字段。后续可迁移对象存储或本地文件。

## 3. API 规划

### Project

```text
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{project_id}
PATCH  /api/v1/projects/{project_id}
DELETE /api/v1/projects/{project_id}
```

### Mount

```text
GET    /api/v1/projects/{project_id}/mounts
POST   /api/v1/projects/{project_id}/mounts
PATCH  /api/v1/projects/{project_id}/mounts/{mount_id}
DELETE /api/v1/projects/{project_id}/mounts/{mount_id}
```

### Session

```text
POST /api/v1/projects/{project_id}/sessions
GET  /api/v1/projects/{project_id}/sessions
```

保留现有 `/sessions` 兼容路径，但新 UI 使用项目维度 API。

### Frontend Project Store（TASK-014 已落地）

```text
web/src/api/modules/projects.ts
web/src/stores/project.ts
web/src/stores/session.ts
```

规则：

- `/projects` 读取 `GET /api/v1/projects`，并按项目拉取 primary Mount 展示授权入口状态。
- `/projects/create` 先创建 Project，再创建 primary Mount；真实 Bridge 仍留到 TASK-018。
- `ProjectBar` 只从 `useProjectStore` 读取当前项目，不保留静态 mock。
- 当前项目 ID 存入 `localStorage: agentforge.current_project_id`，刷新后优先恢复；若失效则回到项目列表第一项。
- `SessionStore` 新建和读取会话时优先走 `/projects/{project_id}/sessions`。

### Pipeline

```text
POST /api/v1/sessions/{session_id}/pipeline-runs
GET  /api/v1/pipeline-runs/{run_id}
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/skip
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/restore
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/start
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/complete
POST /api/v1/pipeline-runs/{run_id}/stages/{stage_id}/fail
```

TASK-015 已落地：`POST /sessions/{id}/chat` 首次发送会创建 PipelineRun，并在响应中返回 `pipeline_run_id`；前端 `StagePreview` 在有 run 时以 `PipelineStageState` 为状态源。

### Artifact

```text
GET  /api/v1/projects/{project_id}/artifacts
GET  /api/v1/artifacts/{artifact_id}
POST /api/v1/projects/{project_id}/artifacts
PATCH /api/v1/artifacts/{artifact_id}
DELETE /api/v1/artifacts/{artifact_id}
```

TASK-016 已落地：StageRuntime 在阶段完成后根据 `stage_id` 映射 `artifact_type`，创建 Artifact，并通过 `artifact_created` SSE 通知前端刷新；前端通过 ArtifactCard 与 Viewer 将 Artifact 加入下一轮 `context_files`，不需要独立 use-as-context API。

### Bridge / Delivery

TASK-018 和 TASK-019 预留：

```text
GET  /api/v1/bridge/status
POST /api/v1/mounts/{mount_id}/read
POST /api/v1/artifacts/{artifact_id}/deliver
```

## 4. SSE 事件规划

新增事件：

```text
pipeline_started
stage_started
stage_completed
stage_skipped
confirm_required
confirm_resolved
artifact_created
bridge_status_changed
delivery_completed
delivery_failed
```

事件原则：

- 所有事件必须带 `project_id`、`session_id`、`pipeline_run_id`。
- `confirm_required` 后 StageRuntime 必须停止自动推进。
- `artifact_created` 是阶段输出归档的唯一前端信号。

## 5. 阶段运行时

StageRuntime 负责把 PipelineRun 和现有 SkillExecutionEngine 连接起来。

职责：

- TASK-015 已实现：执行当前阶段前将 StageState 置为 `running`。
- TASK-015 已实现：调用现有 `SkillExecutionEngine` 执行阶段任务。
- TASK-015 已实现：正常结束后将当前阶段置为 `completed` 并推进 `current_stage_id`。
- TASK-015 已实现：推送 `pipeline_started`、`stage_started`、`stage_completed` SSE 事件。
- TASK-016 已实现：将阶段输出保存为 Artifact，并推送 `artifact_created` SSE。
- TASK-017 继续实现：根据阶段规则判断是否需要确认，并在确认前停止自动推进。
- TASK-018 继续实现：执行当前阶段前加载 Project、Mount、active context 和历史 Artifact。

非职责：

- 不直接读取未授权文件。
- 不直接写入用户本地目录。
- 不决定 UI 样式。

## 6. 风险与修正

| 风险 | 影响 | 处理 |
|------|------|------|
| 继续把 intent 只放进 prompt | 用户以为系统走流程，实际不可控 | TASK-015 建立 PipelineRun |
| Project 前端仍是 mock | 多项目用户无法在 UI 使用真实项目 | TASK-014 接真实 Project API |
| Artifact 只在聊天里 | 产物不可复用 | TASK-016 保存和查看 |
| Bridge 过早接入 | 范围过大，拖慢底座 | TASK-018 延后 |
| 任务状态漂移 | 后续阶段被遗忘 | TASK-012 更新索引和独立任务文件 |

## 7. 文档同步要求

完成 TASK-013 后必须更新：

- `docs/tech-design/DATABASE.md`
- `docs/tech-design/API-SPEC.md`
- `docs/architecture/CORE-DEV-WORKFLOW.md`
- `CLAUDE.md`
- `MEMORY.md`

完成 TASK-014 后必须更新：

- `docs/tech-design/FRONTEND-ARCHITECTURE.md`
- `docs/tasks/CHECKLIST.md`
- `docs/iterations/2026-07-08-core-dev-workflow/TASK-CHECKLIST.md`
- `CLAUDE.md`
- `MEMORY.md`

完成 TASK-015 后必须更新：

- `docs/tech-design/SSE-EXECUTION-VISUALIZATION.md`
- `docs/tech-design/FRONTEND-ARCHITECTURE.md`
- `docs/tech-design/API-SPEC.md`
- `docs/tech-design/DATABASE.md`
- `docs/tasks/CHECKLIST.md`
