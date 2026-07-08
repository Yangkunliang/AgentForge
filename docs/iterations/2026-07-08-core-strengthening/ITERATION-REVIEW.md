# 核心能力增强迭代复盘

**日期**：2026-07-08
**当前完成任务**：TASK-020、TASK-021
**结论**：服务端可信交付巩固与核心交互入口优化已完成，下一步进入 TASK-022 交付能力扩展。

## 完成内容

### TASK-020

- Delivery preview 返回目标文件 fingerprint，包含 `exists`、`size`、`mtime_ns`、`sha256`。
- Delivery apply 支持 `expected_target_hash`，目标文件在预览后变化时返回 409，不覆盖用户文件。
- Delivery 写回冲突或 Bridge 失败时，Artifact 标记为 `delivery_status=failed`，并保存可读失败报告。
- Delivery preview、确认拒绝、成功、冲突和失败均写入 `AuditLog.resource=artifact_delivery`。
- Artifact Viewer 在确认写回时带上预览阶段的 target hash。
- FastAPI 默认启动不再预热远程 E2B 沙箱池；生产需要热池时显式设置 `SANDBOX_POOL_PREWARM_ENABLED=true`。

### TASK-021

- Project 首页新增下一步动作条，按 Mount 连接、进行中 PipelineRun、Artifact 数量提示用户下一步。
- Project 首页最近产物入口从无行为设置按钮调整为可直达 Artifact Viewer。
- Chat 空状态展示当前项目和代码库连接状态，快捷入口改为定位 Bug、开发新功能、迭代优化、UI 调整、架构与选型、代码 Review。
- StagePreview 新增当前阶段摘要，例如“当前：后端开发 · 运行中”。
- ConfirmCard 增加“查看产物并交付”入口；ArtifactCard 增加交付状态标签。
- 新增 `UI-REVIEW.md` 记录 UI/UX 复盘、设计约束和剩余风险。

## 发现并修正的风险

| 风险 | 修正 |
|------|------|
| 用户预览 diff 后，目标文件被外部修改仍可能被覆盖 | apply 支持 expected hash，冲突返回 409 并失败落库 |
| 写回失败只返回 HTTP 错误，不便追溯 | Artifact 保存失败报告，审计日志记录失败 details |
| 默认启动预热 5 个 E2B 云沙箱，增加本地成本和外部依赖 | 新增 `SANDBOX_POOL_PREWARM_ENABLED=false` 默认跳过预热 |
| Project、Stage、Artifact 数据分散，用户需要自行推断下一步 | Project next-action、Stage 摘要、ConfirmCard 交付入口和 Artifact 交付状态显性化 |
| Chat 空状态偏泛用 AI 助手，和全栈开发闭环不够贴合 | 改为当前项目工作台入口，快捷动作对齐需求类型路由 |

## 验证结果

- `uv run --extra dev pytest tests/skills/test_code_executor_pool.py tests/api/test_delivery.py -q`：7 passed
- `uv run --extra dev pytest`：272 passed, 6 skipped, 11 xfailed
- `npm run build`：通过，保留既有 Sass deprecation 和 chunk size warning
- `npm run test:e2e -- artifact-viewer.spec.ts`：3 passed
- `DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:15432/agentforge uv run --extra dev alembic -c migrations/alembic.ini upgrade head`：通过，使用临时 `pgvector/pgvector:pg15` 容器
- `PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18085`：启动到 `AgentForge startup complete ✓`，日志显示 `SandboxPool warmup skipped`
- `npm run test:e2e -- projects.spec.ts human-confirmation.spec.ts pipeline-stage-state.spec.ts --project=chromium`：7 passed

## 下一步

- TASK-022：在本地可信交付稳定后，设计 GitHub PR、zip、upload 等交付扩展。
