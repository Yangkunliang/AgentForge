# TASK-019：写回与交付闭环

**状态**：done
**优先级**：P2
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-016、TASK-018

## 目标

让 AgentForge 的结果回到用户项目中，支持生成 diff、写回授权本地目录、导出测试报告，形成可交付闭环。

## related_requirements

- CDW-07：结果回到项目

## 技术子项

- [x] 新增 DeliveryService
- [x] Artifact 支持 deliver 状态
- [x] 生成 unified diff 预览
- [x] 高风险写操作必须触发用户确认
- [x] Bridge 写入 API 仅允许授权目录内路径
- [x] 写入前做备份或 dry-run
- [x] 写入后生成交付报告
- [x] 可选支持导出 zip 或 markdown 报告（MVP 支持 Markdown 报告）

## acceptance

- [x] 用户可预览即将写入的 diff
- [x] 未确认前不会写入本地文件
- [x] 写入只发生在授权 Mount 内
- [x] 写入完成后生成 Delivery report
- [x] 写入失败有明确错误和恢复建议
- [x] 浏览器 E2E 覆盖 diff 预览和确认写入

## 产出

- 后端新增 `agent_forge.delivery`，支持 Artifact diff preview、确认写回和 Markdown Delivery report。
- `Artifact` 新增 `delivery_status`、`delivery_target_path`、`delivered_at`、`delivery_report` 字段。
- `agent_forge.bridge.files` 新增授权 root 内安全写入，写入前生成 `.agentforge.bak` 备份。
- Artifact Viewer 新增交付面板：选择 connected local Mount、输入目标路径、预览 diff、确认写入、查看报告并导出 Markdown。

## 验证

- `uv run --extra dev pytest tests/api/test_delivery.py`
- `npm run test:e2e -- artifact-viewer.spec.ts`

## 不做

- 不直接提交 git commit。
- 不自动 push。
- 不在 MVP 中创建 GitHub PR。
