# TASK-020：服务端可信交付巩固

**状态**：in_progress
**优先级**：P0
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-STRENGTHENING
**依赖**：TASK-019

## 目标

在 TASK-019 已具备 diff、确认写回和报告导出的基础上，补齐服务端可信交付能力：预览与写入之间的一致性校验、失败状态落库、审计日志和启动/迁移验证，避免用户项目被“看过的 diff 以外的状态”写入。

## related_requirements

- CDW-07：结果回到项目
- CDW-08：写回必须可审计、可解释、可恢复

## 技术子项

- [ ] Delivery preview 返回目标文件 fingerprint（存在性、大小、mtime、sha256）
- [ ] Delivery apply 支持 expected target hash，一旦目标文件在预览后变化则拒绝写入
- [ ] Delivery apply 失败时将 Artifact 标记为 `failed`，并保存可读失败报告
- [ ] Delivery preview/apply/denied/conflict/failure 写入 `AuditLog`
- [ ] Bridge 写入错误、敏感路径拒绝和备份路径进入审计 details
- [ ] Alembic migration smoke test 纳入本任务验收
- [ ] FastAPI 启动验证确保交付路由和依赖无启动期错误

## acceptance

- [ ] 用户预览后，如果目标文件被外部修改，写回 API 返回 409 且不会覆盖用户文件
- [ ] 写回失败后 Artifact 可查询到 `delivery_status=failed` 和失败原因
- [ ] 成功、拒绝、冲突、失败均有 `AuditLog` 可追溯
- [ ] 既有 TASK-019 diff 预览、confirm_write、备份和 Markdown report 行为不回退
- [ ] `uv run --extra dev pytest`、Alembic upgrade smoke、FastAPI 启动检查通过

## 产出

- Delivery response 和 report 增加 target fingerprint。
- `DeliveryApplyRequest` 增加可选一致性校验字段。
- `agent_forge.delivery` 增加失败报告持久化能力。
- Delivery 路由增加审计日志记录。

## 验证

- `uv run --extra dev pytest tests/api/test_delivery.py`
- `uv run --extra dev pytest`
- `uv run --extra dev alembic -c migrations/alembic.ini upgrade head`
- `PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18085`

## 不做

- 不在本任务实现 GitHub PR。
- 不在本任务实现 zip 交付。
- 不改动核心 Agent 编排策略。
