# TASK-050 测试计划

## Preview

- 合法多文件 proposal 生成持久化 ChangeSet/FilePatch、稳定 diff 和基线 sha256，目标文件不变。
- create 文件的基线为不存在；相同内容产生 `has_changes=false`。
- 拒绝重复路径、TaskNode 未声明路径、目录、敏感路径、过大文件、非 UTF-8 目标和总大小超限。
- 拒绝 foreign user/Project、跨 Project Mount/Artifact、non-primary、non-local 和 disconnected Mount。

## Apply

- `confirm_write=false` 返回 409、文件不变、ChangeSet 保持 previewed 并写审计。
- 全部基线先校验；任一文件变化返回 409，所有文件不写，ChangeSet failed。
- 多文件成功写入并返回备份、字节数和 applied 状态；报告和审计无源码正文。
- 第二个文件写入失败时第一个文件恢复，新建文件移除，ChangeSet failed 并记录 rollback。
- applied 重试幂等返回原报告；failed 重试返回 409。

## 回归命令

```bash
uv run pytest -q tests/workspace/test_service.py tests/api/test_workspace.py tests/api/test_delivery.py tests/api/test_projects.py
uv run pytest -q
uv run ruff check --select E,F,I migrations/alembic/versions/021_workspace_change_sets.py src/agent_forge/models/workspace.py src/agent_forge/workspace src/agent_forge/bridge/files.py src/agent_forge/governance/policy.py src/api/routes/workspace.py src/api/main.py
uv run alembic -c migrations/alembic.ini heads
```

代码完成后再次通过 FastAPI startup/shutdown 和 `/api/v1/health` 200 验证。
