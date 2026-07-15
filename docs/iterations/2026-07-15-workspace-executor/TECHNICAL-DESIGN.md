# TASK-050 技术设计：WorkspaceExecutor

## 方案选择

| 方案 | 优点 | 问题 | 结论 |
|---|---|---|---|
| 复用 Artifact Delivery | 改动少 | 单文件、Artifact 归属，无法表达 TaskNode 多文件事务 | 不采用 |
| Skill 直接调用 filesystem/shell | 灵活 | 难以预览、确认、回滚和审计，扩大高风险权限 | 不采用 |
| WorkspaceChangeSet + FilePatch | 结构化、可版本化、可审计，可供 VerificationGate 消费 | 新增模型和 API | 采用 |

## 领域模型

### WorkspaceChangeSet

字段：`id`、`project_id`、`task_graph_id`、`task_node_id`、`mount_id`、可选 `source_artifact_id`、`status`、`apply_report`、`applied_at` 和时间戳。

状态：`previewed -> applying -> applied`；确认拒绝保持 `previewed`；冲突或正常执行异常进入 `failed`。同一 TaskNode 可多次 Preview，每次生成不可覆盖的新版本。

### FilePatch

字段：`id`、`change_set_id`、`target_path`、`operation=upsert`、`proposed_content`、`unified_diff`、`base_exists`、`base_sha256`、`base_size`、`status` 和时间戳。`change_set_id + target_path` 唯一。

第一版不删除和重命名文件。单文件建议上限 200000 UTF-8 bytes，单 ChangeSet 最多 50 个文件、总 proposed content 最多 2000000 bytes。

## 安全边界

1. Graph、Node、Mount 和可选 Artifact 必须属于同一 Project，Project 必须属于当前用户。
2. Mount 必须同时满足 `mount_type=local`、`status=connected`、`role=primary`。
3. 每个 target_path 必须出现在当前 TaskNode.target_files 中；TaskNode 未声明路径时不能 Preview。
4. 路径统一经过 `normalize_mount_relative_path()`，拒绝绝对路径、`..`、符号链接逃逸和敏感文件。
5. Preview 和审计响应不记录 `proposed_content` 或原文件正文；API 返回 unified diff 供用户检查。
6. Apply 通过新的 `GovernancePolicy.evaluate_workspace_confirmation()` 生成 `workspace_write` 决策和影响范围。

## Preview 数据流

```text
POST task-graphs/{graph_id}/nodes/{node_key}/workspace/preview
  -> load TaskNode by current user
  -> validate writable ProjectMount and optional source Artifact
  -> normalize and bound proposals
  -> read current UTF-8 baseline
  -> create unified diff + fingerprint
  -> persist WorkspaceChangeSet + FilePatch[]
  -> AuditLog workspace.preview.succeeded
```

Preview 不调用 `write_mount_file()`。不存在的目标使用 `{exists:false, sha256:null}` 基线；超过安全读取上限或非 UTF-8 目标直接拒绝。

## Apply 数据流

```text
POST workspace-change-sets/{id}/apply
  -> load owned ChangeSet with row lock
  -> Governance confirmation
  -> recheck every FilePatch baseline before any write
  -> mark applying
  -> write changed files with Bridge backup
  -> on normal failure restore already-written originals in reverse order
  -> persist ApplyReport and applied/failed status
  -> AuditLog workspace.apply.*
```

ApplyReport 只记录 `path`、`status`、`created`、`backup_path`、`bytes_written`、错误码、回滚状态和时间，不记录文件内容。已 `applied` 的 ChangeSet 返回已有报告；`failed` 不可重试，必须重新 Preview 以获得新基线。

## API

```http
POST /api/v1/task-graphs/{graph_id}/nodes/{node_key}/workspace/preview
GET  /api/v1/workspace-change-sets/{change_set_id}
POST /api/v1/workspace-change-sets/{change_set_id}/apply
```

Preview 请求：

```json
{
  "mount_id": "mount-001",
  "source_artifact_id": "artifact-code-001",
  "files": [
    {"path": "src/api/routes/notifications.py", "content": "..."}
  ]
}
```

Apply 请求：`{"confirm_write": true}`。资源不存在、跨用户或跨 Project 一律返回 404；确认缺失和基线冲突返回 409；路径和范围错误返回 400/403/413/415。

## 与后续任务的契约

- TASK-051 只消费 `status=applied` 的 ChangeSet、TaskNode.verification_commands 和 Mount，生成 VerificationRun。
- TASK-052 根据 ApplyReport 与 VerificationGateDecision 推进 TaskNode/Stage，不让 WorkspaceExecutor自行完成节点。
- 现有 Artifact Delivery 保持兼容，不与 WorkspaceChangeSet 共用状态字段。

