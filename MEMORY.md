# AgentForge 项目文档索引

## 产品文档 (docs/product/)
- [PRD-v1.md](docs/product/PRD-v1.md) — 产品定位、用户故事、核心功能、技术栈

## 技术设计文档 (docs/design/)
- [ARCHITECTURE.md](docs/design/ARCHITECTURE.md) — Harness 六层架构、消息总线、执行流程
- [API-SPEC.md](docs/design/API-SPEC.md) — 完整 API 规范（认证、任务、Agent、Skill、Dashboard、费用、SSE、Webhook、导出）
- [DATABASE.md](docs/design/DATABASE.md) — 数据库实体（9张表）、索引、关系图
- [SECURITY.md](docs/design/SECURITY.md) — 认证体系、限流、Prompt 注入防护、Skill 沙箱、审计日志
- [LLM-CONFIG.md](docs/design/LLM-CONFIG.md) — LiteLLM 配置、模型路由、Fallback、Cost 追踪
- [DATA-EXPORT.md](docs/design/DATA-EXPORT.md) — 训练数据导出、PII 脱敏策略
- [FRONTEND-ARCHITECTURE.md](docs/design/FRONTEND-ARCHITECTURE.md) — Vue 3 前端架构（SSE 方案、Token 策略、权限模型、Store 同步）
- [RABBITMQ.md](docs/design/RABBITMQ.md) — 消息队列拓扑、Exchange/Queue 设计、消息格式、死信处理
- [DEPLOYMENT.md](docs/design/DEPLOYMENT.md) — 本地开发环境、生产部署、Nginx 配置、数据库迁移

## 任务清单 (docs/tasks/)
- [CHECKLIST.md](docs/tasks/CHECKLIST.md) — 实现任务清单，按 P1→P2→P3→P4 优先级排列，共 28 项

## 迭代记录 (docs/iteration/)
- [ITER-001.md](docs/iteration/ITER-001.md) — 架构设计迭代记录

## 文档体系
- [docs/README.md](docs/README.md) — 文档目录结构、迭代链条、版本号规范

---

## 开发约定

- 实现前先阅读对应设计文档，以文档为准
- 每完成 `CHECKLIST.md` 中一项，立即勾选并单独 commit
- 本地启动顺序：`docker compose up -d` → `alembic upgrade head` → 后端 → 前端（详见 `DEPLOYMENT.md`）
- 前端 API 类型通过 `npm run gen:types` 自动生成，禁止手写
