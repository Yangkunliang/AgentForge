# TASK-049 技术设计：结构化 TaskGraph

## 领域边界

| 对象 | 含义 | 是否复用 |
|---|---|---|
| `Task` | 用户一次请求和成本状态 | 保留，不作为图节点 |
| `SubTask` | 旧 Executor 简单子任务 | 保留，不扩展 |
| `TaskGraph` | 一个 PipelineRun 的结构化执行计划 | 新增 |
| `TaskNode` | 可执行、可验收的工程任务 | 新增 |
| `TaskNodeDependency` | 节点依赖边 | 新增 |

## 数据模型

`TaskGraph`：`id`、`project_id`、`pipeline_run_id`、`source_stage_state_id`、`source_artifact_id`、`schema_version`、`status`、`summary`、时间戳。当前一个 PipelineRun 只允许一个图。

`TaskNode`：`id`、`task_graph_id`、`node_key`、`title`、`description`、`order_index`、`status`、`acceptance_criteria`、`target_files`、`verification_commands`、时间戳。

`TaskNodeDependency`：`task_node_id`、`depends_on_node_id` 联合主键。Service 保证两端属于同一图。

## 输出契约

Catalog 的 `task_split` 增加 `output_contract_key="task_graph_v1"`。可信 system prompt 要求只输出原始 JSON：

```json
{
  "summary": "实现用户通知设置",
  "nodes": [
    {
      "key": "backend-api",
      "title": "新增通知设置 API",
      "description": "实现模型、服务和路由",
      "depends_on": [],
      "acceptance_criteria": ["API 权限和错误响应符合契约"],
      "target_files": ["src/api/routes/notifications.py"],
      "verification_commands": ["pytest -q tests/api/test_notifications.py"]
    }
  ]
}
```

不接受 Markdown fence。Pydantic 校验数量和长度，领域校验保证 key 唯一、依赖存在、无自依赖、无环；目标文件必须是 ProjectMount 内的相对 POSIX 路径，不允许绝对路径或 `..`。

## 事务链

```text
StageRuntime._complete_stage(task_split)
  -> parse_task_graph_output()
  -> complete_stage()
  -> create readable Artifact
  -> create TaskGraph + TaskNode + dependency edges
  -> Artifact.metadata.task_graph_id
  -> commit
```

任一步骤失败由 StageRuntime 统一进入 `_fail_stage()`，事务回滚，不留下 Artifact 或部分节点。

## API

```http
GET /api/v1/pipeline-runs/{run_id}/task-graph
Authorization: Bearer <token>
```

先使用 `get_pipeline_run_for_user_or_404()` 校验 Run 所属用户，再加载图。不存在返回 404；节点按 `order_index` 返回，依赖使用 node key 表示。

## 兼容性

- 非 `task_split` 阶段行为不变。
- 旧 Task/SubTask API 和表不变。
- Artifact 仍使用 `report` 类型和 Markdown 展示。
