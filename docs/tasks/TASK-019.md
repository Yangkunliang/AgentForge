# TASK-019：写回与交付闭环

**状态**：todo
**优先级**：P2
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-016、TASK-018

## 目标

让 AgentForge 的结果回到用户项目中，支持生成 diff、写回授权本地目录、导出测试报告，形成可交付闭环。

## related_requirements

- CDW-07：结果回到项目

## 技术子项

- [ ] 新增 DeliveryService
- [ ] Artifact 支持 deliver 状态
- [ ] 生成 unified diff 预览
- [ ] 高风险写操作必须触发用户确认
- [ ] Bridge 写入 API 仅允许授权目录内路径
- [ ] 写入前做备份或 dry-run
- [ ] 写入后生成交付报告
- [ ] 可选支持导出 zip 或 markdown 报告

## acceptance

- [ ] 用户可预览即将写入的 diff
- [ ] 未确认前不会写入本地文件
- [ ] 写入只发生在授权 Mount 内
- [ ] 写入完成后生成 Delivery report
- [ ] 写入失败有明确错误和恢复建议
- [ ] 浏览器 E2E 覆盖 diff 预览和确认写入

## 不做

- 不直接提交 git commit。
- 不自动 push。
- 不在 MVP 中创建 GitHub PR。
