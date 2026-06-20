# AgentForge

**AgentForge** — 面向生产的多智能体协同框架。

**当前重心**：全栈开发自动化。

---

## 目录结构

```
docs/
├── standards/      # 长期规范：文档、迭代、Skill 使用策略
├── architecture/   # 当前系统架构蓝图
├── product-design/   # 产品文档
├── tech-design/   # 技术设计文档
├── iteration/     # 迭代记录
└── iterations/    # 新迭代产物目录
```

## 长期规范 (standards/)

| 文档 | 说明 | 状态 |
|------|------|------|
| ITERATION-STANDARD.md | 迭代目录、产物命名、checklist 字段、小步提交、本地 UI/UX Skill 使用策略 | ✅ |
| DEVELOPMENT-GUIDE.md | 环境配置、启动步骤、测试方法、开发规范 | ✅ |

## 当前系统架构 (architecture/)

| 文档 | 说明 | 状态 |
|------|------|------|
| AGENT-MODEL.md | AgentForge 产品内部的 Agent 定义、类型、能力模型、协作机制 | ✅ |

## 设计文档清单 (tech-design/)

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

1. **PRODUCT-REQUIREMENTS.md** → 产品需求（做什么）
2. **TASK-CHECKLIST.md** → 任务拆解、优先级、验收标准
3. **TECHNICAL-DESIGN.md** → 技术方案（怎么实现）
4. **UI-DESIGN.md** → UI/UX 设计（仅 UI 相关迭代需要）
5. **TEST-PLAN.md** → 测试与验收方案
6. **ITERATION-REVIEW.md** → 迭代总结（学到了什么）

## 版本号规范

- 新迭代目录：`docs/iterations/YYYY-MM-DD-topic/`
- 标准产物：`PRODUCT-REQUIREMENTS.md`、`TASK-CHECKLIST.md`、`TECHNICAL-DESIGN.md`、`TEST-PLAN.md`、`ITERATION-REVIEW.md`
- UI 相关迭代增加：`UI-DESIGN.md`
- 历史 `PRD-*`、`TASK-*`、`TEST-*`、`ITER-*` 文件保留可追溯，后续新迭代使用新命名规范
