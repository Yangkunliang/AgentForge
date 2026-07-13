# TASK-044 产品需求：Artifact 运行时来源固化

## 背景

TASK-033 到 TASK-043 已经把 AgentProfile、ModelRoute、SkillPolicy、高风险授权和 EvalFeedback 串入运行时。当前不足是：产物详情页只能看到 Pipeline / Session / 阶段基础信息，生成该产物时使用的 Agent、模型路由和 SkillPolicy 主要散落在 StageState / EvalEvent 中。

## 用户价值

全栈开发工程师查看 PRD、技术方案、代码 diff 或测试报告时，需要快速判断这份产物由哪个运行时配置生成，便于复盘、追责、比较模型效果和决定是否交付。

## 范围

- 阶段完成创建 Artifact 时，将非敏感运行来源写入 `metadata.runtime`。
- Artifact 详情页展示 Agent、模型和路由来源。
- 不新增数据库字段，不复制 API Key、Credential secret 或完整 prompt。

## 验收标准

- StageRuntime 创建的 Artifact metadata 包含 AgentProfile、ModelRoute、model name 和 skill policy key。
- Artifact API 原有 `metadata` 响应继续兼容手动创建产物。
- 前端构建通过，产物详情页能在存在 runtime metadata 时展示来源。
