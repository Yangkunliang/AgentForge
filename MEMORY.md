# 多智能体框架项目文档索引

## 产品文档 (product-design/)
- [PRD-多智能体框架 - 产品需求文档](product-design/PRD-多智能体框架-20260617.md) — 产品定位、用户故事、核心功能、技术栈

## 技术设计文档 (tech-design/)
- [ARCHITECTURE.md](tech-design/ARCHITECTURE.md) — Harness 六层架构 + 消息总线 + 数据导出 + LLM 抽象
- [AGENTS.md](tech-design/AGENTS.md) — Agent 定义、类型、能力模型、协作机制
- [API-SPEC.md](tech-design/API-SPEC.md) — API 规范、分页、Webhook、SSE 流式输出、错误码
- [DATABASE.md](tech-design/DATABASE.md) — 数据库实体、索引、关系图
- [SECURITY.md](tech-design/SECURITY.md) — 认证、限流、沙箱、Secrets 管理
- [LLM-CONFIG.md](tech-design/LLM-CONFIG.md) — LiteLLM 配置、模型选择、Fallback、Cost 追踪
- [DATA-EXPORT.md](tech-design/DATA-EXPORT.md) — 训练数据导出、脱敏、模型训练用途

## 迭代记录 (iteration/)
- [架构设计迭代记录](iteration/ITER-架构设计-20260617.md) — 架构设计迭代总结

## 文档体系 (docs/)
- [README.md](docs/README.md) — 文档迭代链条、版本号规范

## 迭代执行约定
- 后续每一次迭代开始前，先设计任务 checklist，按模块和优先级排序。
- 每个 checklist item 需要明确模块、优先级、产出物和验收标准。
- 执行时遵循小步提交：完成 1 个 checklist item 后，立即勾选完成并单独 commit 一次。
- 架构设计阶段也遵循该流程，先完成设计 checklist，再进入开发执行。
