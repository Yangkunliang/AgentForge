# 核心能力增强技术设计

**日期**：2026-07-08
**关联架构**：`docs/architecture/CORE-DEV-WORKFLOW.md`
**状态**：方案设计

## 1. 总体策略

TASK-020 至 TASK-022 是核心闭环完成后的增强阶段。它不改变主链路：

```text
Project -> Mount -> Session -> PipelineRun -> StageState -> Artifact -> Delivery
```

增强顺序按风险排序：先加固 Delivery 写回可信度，再优化用户交互，最后扩展远程和打包交付。

## 2. TASK-020 服务端可信交付

### 2.1 Preview fingerprint

Delivery preview 读取目标文件时生成 fingerprint：

```text
exists
size
mtime_ns
sha256
```

其中 `sha256` 代表用户预览时看到的目标文件内容。目标不存在时 `exists=false` 且 `sha256=null`。

### 2.2 Apply consistency check

Delivery apply 增加可选 `expected_target_hash`：

```text
POST /api/v1/artifacts/{artifact_id}/delivery/apply
{
  "mount_id": "...",
  "target_path": "src/main.py",
  "confirm_write": true,
  "expected_target_hash": "<preview report target sha256>"
}
```

如果请求提供了 hash，服务端会在写入前重新读取目标 fingerprint。当前 hash 与 expected 不一致时，拒绝写入，返回 409，并将 Artifact 标记为 `failed`，保存失败报告。

### 2.3 Failure report

失败报告写入 `Artifact.delivery_report`：

```text
status
phase
target_path
mount_id
error_code
error_message
recovery_hint
target_fingerprint
```

报告目标是给用户明确解释“为什么没有写入”和“下一步怎么恢复”，而不是只返回 HTTP 错误。

### 2.4 AuditLog

Delivery 路由写入审计日志：

```text
delivery.preview.succeeded
delivery.apply.denied
delivery.apply.succeeded
delivery.apply.conflict
delivery.apply.failed
```

`details` 包含 artifact、project、mount、target_path、backup_path、fingerprint、error 等信息。审计日志不记录 Artifact 内容。

## 3. TASK-021 交互设计复盘

UI 复盘只解决核心工作流入口，不做视觉重写。重点对象：

- Project 首页：当前项目状态、Mount 健康、进行中 Pipeline、最近 Artifact。
- Chat：空状态、阶段状态、确认卡片、阶段完成卡片。
- Artifact Viewer：从查看、复用到交付的动作顺序。
- Delivery 面板：preview/apply 冲突或失败时的恢复提示。

## 4. TASK-022 交付扩展

GitHub / zip / upload 交付都必须遵守 Mount 主动授权原则：

- GitHub Mount 只能访问用户 OAuth 授权的 repo。
- GitHub PR Delivery 必须先生成 diff，再由用户确认创建 branch/commit/PR。
- zip Delivery 不写用户目录，只导出可下载交付包。
- upload Mount 仅用于用户主动上传的文件集合，不推断本地路径。

## 5. 验证策略

- 服务端改动必须跑全量 `uv run --extra dev pytest`。
- FastAPI 路由、配置或依赖改动必须跑 uvicorn 启动检查。
- 迁移或模型相关改动必须跑 Alembic upgrade smoke。
- 前端改动必须跑 `npm run build`，涉及用户流程时补充 Playwright E2E。
