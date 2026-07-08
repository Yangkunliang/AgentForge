# TASK-017：人工确认与阶段继续机制

**状态**：todo
**优先级**：P1
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-015、TASK-016

## 目标

把 PRD 确认、技术选型确认、影响范围确认做成真实流程节点。Agent 在确认点必须暂停，用户确认或修改后才能继续。

## related_requirements

- CDW-05：关键节点人工确认

## 技术子项

- [ ] StageState 支持 `waiting_confirmation`
- [ ] 新增 `confirm_required` / `confirm_resolved` SSE 事件
- [ ] ConfirmCard 接真实事件渲染
- [ ] 新增确认 API：确认继续、提出修改意见、取消执行
- [ ] StageRuntime 在确认前停止自动推进
- [ ] 用户修改意见写入下一阶段上下文
- [ ] 审计日志记录确认操作

## acceptance

- [ ] PRD 阶段完成后触发确认卡片
- [ ] 用户确认后进入下一阶段
- [ ] 用户提出修改意见后同阶段重新执行或追加修订
- [ ] 未确认时不会继续执行后续阶段
- [ ] 确认操作有审计记录
- [ ] 浏览器 E2E 覆盖暂停和继续

## 不做

- 不做多人审批。
- 不做复杂审批流模板。
- 不做 GitHub PR review。
