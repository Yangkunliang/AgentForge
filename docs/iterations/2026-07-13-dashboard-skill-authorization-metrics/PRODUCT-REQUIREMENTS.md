# TASK-042 产品需求：Dashboard 高风险 Skill 授权指标

## 背景

TASK-038 至 TASK-041 已完成高风险 Skill 临时授权、前端确认入口、EvalEvent 记录和 Evaluation summary 聚合。当前不足是：授权频率、通过率和高风险权限分布只能通过 API 观察，平台用户和平台维护者无法在 Dashboard 直接判断策略是否过严或过松。

## 目标

- 在 Dashboard 展示高风险 Skill 授权概览。
- 帮助用户快速看到授权请求数、已授权数、授权通过率。
- 展示最常触发授权的 Skill 和 permission，作为后续策略优化依据。

## 非目标

- 不新增告警、阈值配置或自动策略调优。
- 不改 EvalEvent 表结构。
- 不新增独立 Evaluation 页面。

## 验收标准

- `/api/v1/dashboard` 的 `evaluation` 字段返回 `skill_authorizations` 聚合块。
- Dashboard 页面在无授权事件时展示 0 值和空态，不出现空白或 undefined。
- Dashboard 页面在有授权事件时展示总览、按 Skill 排行和按 permission 排行。
- 保持现有 Dashboard 任务、费用、Agent & Skill、最近任务展示不回退。
