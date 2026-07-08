# 核心能力增强测试计划

**日期**：2026-07-08
**范围**：TASK-020 至 TASK-026

## TASK-020 服务端可信交付

| 验收项 | 自动化验证 |
|--------|------------|
| preview 返回 fingerprint | `uv run --extra dev pytest tests/api/test_delivery.py` |
| apply 提供 expected hash 且目标被改动时返回 409 | `uv run --extra dev pytest tests/api/test_delivery.py` |
| conflict 不覆盖用户文件 | `uv run --extra dev pytest tests/api/test_delivery.py` |
| BridgeAccessError 会写入 failed report | `uv run --extra dev pytest tests/api/test_delivery.py` |
| preview/apply/denied/conflict/succeeded 写入 AuditLog | `uv run --extra dev pytest tests/api/test_delivery.py` |
| 全量回归 | `uv run --extra dev pytest` |
| 迁移 smoke | `uv run --extra dev alembic -c migrations/alembic.ini upgrade head` |
| FastAPI 启动 | `PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18085` |

## TASK-021 核心交互设计复盘

| 验收项 | 自动化验证 |
|--------|------------|
| Project 首页关键入口可见 | Playwright E2E |
| Chat 阶段完成后 Artifact/确认/交付入口可达 | Playwright E2E |
| Delivery 冲突或失败提示可读 | Playwright E2E |
| 前端构建 | `npm run build` |

## TASK-022 交付能力扩展

| 验收项 | 自动化验证 |
|--------|------------|
| GitHub OAuth Mount 权限边界 | TASK-023 后端 API 测试 |
| GitHub PR Delivery 不绕过确认 | TASK-024 后端 API 测试 + E2E |
| zip 交付包可下载且内容正确 | TASK-025 后端 API 测试 |
| upload Mount 不访问本地路径 | TASK-026 后端 API 测试 |
| 扩展设计与任务拆分完整 | `git diff --check` + 文档路径检查 |

## TASK-023 GitHub OAuth Mount 授权底座

| 验收项 | 自动化验证 |
|--------|------------|
| OAuth start 创建 state 并写审计，不泄露 token | `uv run --extra dev pytest tests/api/test_github_mount.py` |
| OAuth start 拒绝外部 redirect_uri | `uv run --extra dev pytest tests/api/test_github_mount.py` |
| OAuth callback 创建 connected GitHub Mount，token 只服务端加密存储 | `uv run --extra dev pytest tests/api/test_github_mount.py` |
| 重复 state 被拒绝 | `uv run --extra dev pytest tests/api/test_github_mount.py` |
| 删除 GitHub Mount 标记 credential revoked 并写审计 | `uv run --extra dev pytest tests/api/test_github_mount.py` |
| Project 创建向导选择 GitHub 时调用 OAuth start 而非普通 mount | `npm run test:e2e -- projects.spec.ts --project=chromium` |
| 迁移 smoke | `DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:15432/agentforge uv run --extra dev alembic -c migrations/alembic.ini upgrade head` |
| FastAPI 启动 | `PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18086` |

## TASK-024 GitHub PR Delivery

| 验收项 | 自动化验证 |
|--------|------------|
| GitHub PR preview 返回 diff、base sha、目标分支和 PR 摘要 | `uv run --extra dev pytest tests/api/test_github_delivery.py` |
| apply 未确认时返回 409 且不创建 branch/commit/PR | `uv run --extra dev pytest tests/api/test_github_delivery.py` |
| base sha 变化时返回 409，Artifact 保存 failed report | `uv run --extra dev pytest tests/api/test_github_delivery.py` |
| apply 成功创建 branch、commit、PR，并保存 PR URL / commit sha | `uv run --extra dev pytest tests/api/test_github_delivery.py` |
| GitHub token 不进入响应或 AuditLog details | `uv run --extra dev pytest tests/api/test_github_delivery.py` |
| Artifact Viewer 可切换到 GitHub PR Delivery 并提交 expected_base_sha | `npm run test:e2e -- artifact-viewer.spec.ts --project=chromium` |
| 前端构建 | `npm run build` |

## TASK-025 zip Delivery Package

| 验收项 | 自动化验证 |
|--------|------------|
| zip preview 返回 package_name、file_count、total_bytes、package_sha256 且不落地文件 | `uv run --extra dev pytest tests/api/test_zip_delivery.py` |
| apply 未确认时返回 409，不生成 zip | `uv run --extra dev pytest tests/api/test_zip_delivery.py` |
| apply 成功生成 manifest、delivery-report.md 和 files/ 内容，并保存 Delivery report | `uv run --extra dev pytest tests/api/test_zip_delivery.py` |
| 包内路径拒绝绝对路径、`..`、空路径、反斜杠、Windows 盘符、控制字符和重复路径 | `uv run --extra dev pytest tests/api/test_zip_delivery.py` |
| 下载接口按 Artifact/Project 用户权限隔离，不暴露服务器临时路径 | `uv run --extra dev pytest tests/api/test_zip_delivery.py` |
| 过期 zip 在后续 apply 前清理 | `uv run --extra dev pytest tests/api/test_zip_delivery.py` |
| Artifact Viewer 可切换到 zip 包模式、生成并下载 zip | `npm run test:e2e -- artifact-viewer.spec.ts --project=chromium` |
| 前端构建 | `npm run build` |

## TASK-026 Upload Mount 上下文兜底

| 验收项 | 自动化验证 |
|--------|------------|
| multipart 上传创建 connected upload Mount，并保存 manifest | `uv run --extra dev pytest tests/api/test_upload_mount.py` |
| Bridge list/read 只读取 manifest 内路径 | `uv run --extra dev pytest tests/api/test_upload_mount.py` |
| 路径穿越、反斜杠、非法扩展、超限、非 UTF-8 被拒绝 | `uv run --extra dev pytest tests/api/test_upload_mount.py` |
| 跨用户访问 upload Mount 返回 404 | `uv run --extra dev pytest tests/api/test_upload_mount.py` |
| 删除 Upload Mount 清理文件并写审计 | `uv run --extra dev pytest tests/api/test_upload_mount.py` |
| Project 创建向导可创建 upload Mount | `npm run test:e2e -- projects.spec.ts --project=chromium` |
| ContextPicker 可选择 upload Mount 文件并进入 chat payload | `npm run test:e2e -- bridge-context.spec.ts --project=chromium` |
| 前端构建 | `npm run build` |

## 非目标

- 不把外部 GitHub API 调用放进无隔离的单元测试。
- 不使用真实用户目录做破坏性写入。
- 不把敏感 token 或 Artifact 内容写入审计日志。
