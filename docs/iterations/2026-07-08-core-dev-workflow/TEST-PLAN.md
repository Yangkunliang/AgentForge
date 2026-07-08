# 核心开发闭环测试与验收计划

**日期**：2026-07-08
**范围**：TASK-012 至 TASK-019 的分阶段验收设计

## 1. TASK-012 文档验收

| 验收项 | 命令或方式 |
|--------|------------|
| 新迭代目录符合规范 | 检查 `docs/iterations/2026-07-08-core-dev-workflow/` |
| TASK-013 至 TASK-019 不会遗忘 | 检查 `docs/tasks/CHECKLIST.md` 和独立任务文件 |
| TASK-007 状态漂移已说明 | 检查 `docs/tasks/TASK-007.md` |
| 架构文档已建立 | 检查 `docs/architecture/CORE-DEV-WORKFLOW.md` |
| 文档索引已更新 | 检查 `docs/README.md`、`MEMORY.md`、`CLAUDE.md` |

## 2. 后续任务验收矩阵

| 任务 | 自动化验证 | 浏览器验收 | 文档验收 |
|------|------------|------------|----------|
| TASK-013 | pytest 覆盖模型、迁移、API 权限 | 无 | DATABASE/API-SPEC 更新 |
| TASK-014 | 前端 build、API mock 测试 | Project 列表、创建、切换项目 | FRONTEND-ARCHITECTURE 更新 |
| TASK-015 | pytest 覆盖 PipelineRun 状态机 | 阶段条真实状态变化 | SSE/API 事件更新 |
| TASK-016 | pytest 覆盖 Artifact CRUD | Artifact Viewer 可查看 | Artifact 类型说明 |
| TASK-017 | pytest 覆盖 confirm_required/confirm_resolved、确认 API、等待态防绕过 | `human-confirmation.spec.ts` 覆盖确认继续和提交修改意见 | 人工介入点更新 |
| TASK-018 | Bridge 单测和权限测试 | Mount 连接状态、文件读取 | 安全文档更新 |
| TASK-019 | Delivery service 单测 | diff/导出/写回操作确认 | 交付边界更新 |

## 3. 端到端验收目标

核心闭环完成后必须有一条 E2E 覆盖：

```text
创建项目 -> 创建会话 -> 选择 intent -> 创建 PipelineRun
-> 阶段开始 -> 生成 Artifact -> confirm_required
-> 用户确认 -> 下一阶段开始 -> 查看 Artifact
```

TASK-018 已补充：

```text
创建 connected local Mount -> 从授权 root 列文件 -> 读取授权文件
-> Chat context_files 携带 mount_id -> SkillExecutionEngine 收到真实文件内容
```

TASK-019 继续补充 Artifact 写回、导出 diff 和交付报告路径。

## 4. 非阻塞警告

以下警告不阻塞 TASK-012：

- 现有 Sass `@import` deprecation。
- 现有 pytest 中 xfail/skip 项。
- 现有 TASK-001 至 TASK-011 历史文档命名不完全一致。

但 TASK-013 之后的代码任务必须继续满足：

- 后端变更跑 `uv run --extra dev pytest`。
- 前端变更跑 `cd web && npm run build`。
- FastAPI 路由变更跑 `PYTHONPATH=src uvicorn api.main:app` 启动检查。
