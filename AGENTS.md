# AgentForge 仓库级 Agent 工作规范

## 1. 项目定位

AgentForge 是面向生产的多智能体协同框架，**面向全栈开发工程师的平台产品**。

### 两个视角的区分（重要）

在这个仓库里存在两个截然不同的视角，Agent 必须时刻清楚当前在哪个视角下工作：

| 视角 | 说明 | 典型任务 |
|------|------|---------|
| **开发视角** | 开发 AgentForge 平台本身 | 实现 Skill Engine、写 FastAPI 路由、设计数据库 Schema |
| **用户视角** | 设计平台终端用户的使用体验 | 设计项目管理页面、设计 Agent 对话交互、规划用户流水线 |

**平台的终端用户是全栈开发工程师**，他们用 AgentForge 来开发自己的项目，而不是来开发 AgentForge 本身。做用户视角的功能设计时，必须站在这些用户的角度思考，而不是以"开发 AgentForge 的工程师"自居。

### 用户画像

| 类型 | 场景 | 代码库特征 |
|------|------|-----------|
| 独立开发者 | 维护自己的 SaaS 产品 | 前后端可能在不同本地目录 |
| 创业团队成员 | 多个微服务 / Monorepo | 需要跨服务理解代码依赖 |
| 外包接单开发者 | 同时维护多个客户项目 | 需要频繁切换项目上下文 |

---

## 2. 工作原则

- **架构先行**：先明确范围、模块边界、数据流、接口和验收标准，再进入实现。
- **小步迭代**：每次迭代先建立任务 checklist，按模块和优先级排序。
- **小步提交**：完成 1 个 checklist item 后，立即勾选完成并单独 commit 一次。
- **文档同步**：目录、规范、架构和迭代产物发生变化时，同步更新 `docs/README.md` 与 `MEMORY.md`。
- **避免混淆**：根目录 `AGENTS.md` 只放仓库级 Agent 工作规范；AgentForge 产品中的 Agent 领域模型放在 `docs/architecture/AGENT-MODEL.md`。

---

## 3. 平台核心设计约束

做任何功能设计、页面原型、数据模型时，必须遵守以下约束：

### 3.1 「项目」是平台一等公民

- 用户的每个代码库在 AgentForge 里对应一个「项目（Project）」
- 所有对话（Session）、历史产物（PRD、代码、测试报告）都归属到某个项目下
- 用户可以在平台内管理多个项目，建议上限 3 个同时活跃项目
- 项目展示名称由用户自定义（如「我的电商后端」），而不是裸路径（如 `~/work/shop-api`）

### 3.2 代码库访问是用户主动授权的

用户通过以下方式之一授权 Agent 访问其代码库，不存在平台自动扫描：

| 方式 | 适用场景 | 优先级 |
|------|---------|-------|
| CLI 工具（`agentforge mount <路径>`） | 本地目录，开发者友好 | 推荐 |
| 桌面客户端目录选择器 | 本地目录，GUI 操作 | 推荐 |
| GitHub OAuth 连接 | 远程仓库，无需本地环境 | 推荐 |
| 手动上传关键文件 | 以上方案不可用时的兜底 | 兜底 |

### 3.3 需求类型路由

Agent 收到用户需求后，**第一步是意图分类**，而不是直接开始执行。根据分类结果动态组合流水线阶段：

| 需求类型 | 触发信号 | 执行阶段 |
|---------|---------|---------|
| 全新功能 | 新实体/新表、新路由、跨模块改动 | 需求分析 → 架构设计 → DB & API → 任务拆解 → UI 原型 → 后端开发 → 前端开发 → 测试交付 |
| 迭代优化 | 改现有逻辑、不加新表、改动局部 | 需求 Diff → 影响评估* → 后端开发 → 前端开发* → 回归测试 |
| UI 调整 | 只改前端文件、不动接口和数据库 | 原型 Diff → 前端开发 → 视觉验收 |
| Bug / 重构 | 明确报错 / 性能问题 / 代码坏味道 | 问题定位 → 影响范围分析 → 修复 → 回归测试 |

> `*` 为可选阶段，Agent 根据需求自动判断是否需要。

### 3.4 人工介入点

以下节点需要暂停等待用户确认，不得自动跳过：

1. **PRD / 需求 Diff 确认** — 所有后续阶段的基础，错了会放大
2. **技术选型确认** — 是否引入新中间件/服务，影响工作量倍数
3. **影响范围确认** — 修改前先让用户看清楚会动哪些文件

### 3.5 上下文管理

- Agent 不全量读取项目目录，根据当前需求按需索引相关文件
- 多目录场景（如前后端分离）：每个目录挂载时用户需标注角色（主项目 / 参考项目 / 文档库）
- 同名文件来自不同目录时，必须显示完整相对路径加以区分，避免 Agent 混淆

---

## 4. 文档目录约定

- `docs/standards/`：长期规范，例如文档命名、迭代流程、提交节奏、Skill 使用策略。
- `docs/architecture/`：当前系统架构蓝图，例如 Agent 模型、Harness、API、数据库、安全、前端架构。
- `docs/iterations/`：每次迭代生成的过程文档，按日期和主题建目录。
- `docs/product-design/`、`docs/tech-design/`、`docs/iteration/`：历史文档目录，迁移时应保持索引可追溯。

---

## 5. 迭代产物命名

新迭代目录建议使用以下文件名：

```text
docs/iterations/YYYY-MM-DD-topic/
├── PRODUCT-REQUIREMENTS.md
├── TASK-CHECKLIST.md
├── TECHNICAL-DESIGN.md
├── UI-DESIGN.md
├── TEST-PLAN.md
└── ITERATION-REVIEW.md
```

`UI-DESIGN.md` 仅在涉及 UI/UX 时创建。

---

## 6. 本地 UI/UX Skill 使用约束

前端 UI/UX 设计类任务允许使用本地已安装的 `ui-ux-pro-max` skill：

```text
~/.claude/skills/ui-ux-pro-max
```

使用边界：

- 仅作为 advisory skill 使用。
- 仅用于 UI design、UX review、design system、frontend visual spec 等任务。
- 输出必须沉淀到 `UI-DESIGN.md` 或 `UI-REVIEW.md`。
- 不得用于后端架构、数据库、安全、部署、Agent 编排或核心领域模型决策。
- 该 skill 属于开发过程辅助能力，不默认进入 AgentForge 产品运行时的 SkillRegistry。

---

## 7. Git 凭证

**本地已配置 `store` credential helper**，`~/.git-credentials` 存有 GitHub PAT。

```bash
# 凭证文件
cat ~/.git-credentials
# https://<USER>:<PAT>@github.com
```

**Push 失败时的兜底方案**（当 `store` helper 未自动匹配 remote URL 时）：

```bash
git push https://<PAT>@github.com/<owner>/<repo>.git <branch>
```

> PAT 以 `gho_` 开头（Fine-grained）或 `ghp_` 开头（classic），scope 需包含 `repo`。
> 如凭证文件中无 GitHub 条目，先引导用户从 https://github.com/settings/tokens 创建并保存：
> ```bash
> echo "https://<PAT>@github.com" >> ~/.git-credentials
> git config --global credential.helper store
> ```

---

## 8. 验证要求

文档类变更至少检查：

- 链接和路径是否准确。
- 规范与目录结构是否一致。
- 是否存在同名但语义不同的文档。
- 是否更新了相关索引。

---

## 8.1 代码变更必须可启动（重要）

每次完成代码修改后，**必须确保项目可以正常启动**，不得把错误留给用户。

具体要求：

- 修改涉及 FastAPI 路由、配置、中间件、依赖引入等时，修改完成后必须通过 `PYTHONPATH=.../src uvicorn api.main:app` 验证启动成功，确认无 `ImportError`、`NameError`、`Exception` 等启动期报错。
- 修改涉及前端时，必须通过 `cd web && npm run build` 确认构建成功。
- **如果启动失败，必须当场修复错误并再次验证**，不得在仍有错误的状态下让代码进入未 commit 的工作树供用户检查。
- 不允许「改完代码就结束对话，等用户自己启动发现 bug 再回来修」的工作流。

> 原则：交付给用户的代码必须是**可运行的**，不是「改了一半的半成品」。

---

## 9. 架构变更自动同步

当对话中产生**架构级别**变更时，Agent 应主动同步更新架构文档，无需用户额外指示。

**触发条件**（满足任一即触发）：

- 新增、删除或重命名模块/子系统
- 模块间接口或数据流变更
- 数据模型（表结构、核心实体）调整
- 技术选型变更（框架、中间件、数据库、协议等）
- 部署架构或基础设施变更
- **平台产品定位或用户画像发生变化**（新增）

**不触发**：bug 修复、小功能增强、样式调整、依赖升级等非架构变更。

**同步目标**：

- `docs/architecture/` 下相关架构文档
- `MEMORY.md`（若涉及架构概要变更）
- `CLAUDE.md`（若涉及架构概要、技术栈或产品定位变更）
- `AGENTS.md`（若涉及平台设计约束变更）

**执行节奏**：在变更完成后立即同步，与代码变更在同一次 commit 中提交。
