# AgentForge

**AgentForge** — 面向生产的多智能体协同框架。

**当前重心**：全栈开发自动化。

---

## 目录结构

```
docs/
├── product/           # 产品文档
├── design/            # 技术设计文档
├── tasks/             # 任务拆解文档
├── tests/             # 测试用例文档
├── api/               # API 文档
└── iteration/         # 迭代记录
```

## 设计文档清单 (docs/design/)

| 文档 | 说明 | 状态 |
|------|------|------|
| ARCHITECTURE.md | 整体架构、六层 Harness、执行流程 | ✅ |
| DATABASE.md | 数据库实体、索引、关系图 | ✅ |
| API-SPEC.md | 完整 API 规范（含注册、Dashboard、反馈、费用、Skill 安装进度） | ✅ |
| SECURITY.md | 认证、限流、沙箱、Secrets 管理 | ✅ |
| LLM-CONFIG.md | LLM Provider、模型路由、Cost 追踪 | ✅ |
| DATA-EXPORT.md | 训练数据导出、脱敏策略 | ✅ |
| FRONTEND-ARCHITECTURE.md | 前端架构（含 SSE 方案、Token 策略、权限模型、Store 同步） | ✅ |
| RABBITMQ.md | 消息队列拓扑、Exchange/Queue 设计、消息格式、死信处理 | ✅ |
| DEPLOYMENT.md | 本地开发环境、生产部署、Nginx 配置、数据库迁移 | ✅ |

## 迭代链条

每个功能迭代遵循完整链条：

1. **PRD** → 产品需求（做什么）
2. **Task** → 任务拆解（怎么拆）
3. **Design** → 技术方案（怎么实现）
4. **Test** → 测试用例（怎么验证）
5. **Iteration** → 迭代总结（学到了什么）

## 版本号规范

- PRD: `PRD-v{n}.md`（如 PRD-v1.md）
- Task: `TASK-{task-name}-{timestamp}.yaml`（如 TASK-login-feature-20260619.yaml）
- Test: `TEST-{test-name}-{timestamp}.md`（如 TEST-user-auth-20260619.md）
- Iteration: `ITER-{task-name}-{timestamp}.md`（如 ITER-architecture-design-20260619.md）
