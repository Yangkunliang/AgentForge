# 核心能力增强迭代复盘

**日期**：2026-07-08
**当前完成任务**：TASK-020
**结论**：服务端可信交付巩固已完成，下一步进入 TASK-021 核心交互设计复盘。

## 完成内容

- Delivery preview 返回目标文件 fingerprint，包含 `exists`、`size`、`mtime_ns`、`sha256`。
- Delivery apply 支持 `expected_target_hash`，目标文件在预览后变化时返回 409，不覆盖用户文件。
- Delivery 写回冲突或 Bridge 失败时，Artifact 标记为 `delivery_status=failed`，并保存可读失败报告。
- Delivery preview、确认拒绝、成功、冲突和失败均写入 `AuditLog.resource=artifact_delivery`。
- Artifact Viewer 在确认写回时带上预览阶段的 target hash。
- FastAPI 默认启动不再预热远程 E2B 沙箱池；生产需要热池时显式设置 `SANDBOX_POOL_PREWARM_ENABLED=true`。

## 发现并修正的风险

| 风险 | 修正 |
|------|------|
| 用户预览 diff 后，目标文件被外部修改仍可能被覆盖 | apply 支持 expected hash，冲突返回 409 并失败落库 |
| 写回失败只返回 HTTP 错误，不便追溯 | Artifact 保存失败报告，审计日志记录失败 details |
| 默认启动预热 5 个 E2B 云沙箱，增加本地成本和外部依赖 | 新增 `SANDBOX_POOL_PREWARM_ENABLED=false` 默认跳过预热 |

## 验证结果

- `uv run --extra dev pytest tests/skills/test_code_executor_pool.py tests/api/test_delivery.py -q`：7 passed
- `uv run --extra dev pytest`：272 passed, 6 skipped, 11 xfailed
- `npm run build`：通过，保留既有 Sass deprecation 和 chunk size warning
- `npm run test:e2e -- artifact-viewer.spec.ts`：3 passed
- `DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:15432/agentforge uv run --extra dev alembic -c migrations/alembic.ini upgrade head`：通过，使用临时 `pgvector/pgvector:pg15` 容器
- `PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18085`：启动到 `AgentForge startup complete ✓`，日志显示 `SandboxPool warmup skipped`

## 下一步

- TASK-021：从全栈开发工程师视角复盘 Project、Chat、Stage、Artifact、Delivery 的下一步动作和关键入口。
- TASK-022：在本地可信交付稳定后，设计 GitHub PR、zip、upload 等交付扩展。
