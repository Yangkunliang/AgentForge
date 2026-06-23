# TASK-007：全栈 Agent 交互体验 — 静态页面

**状态**：进行中  
**优先级**：P2  
**创建日期**：2026-06-23  
**关联 PRD**：[PRD-全栈Agent交互体验-20260623.md](../product-design/PRD-全栈Agent交互体验-20260623.md)  
**依赖任务**：TASK-005（前端工程基础）、TASK-006（Chat UI 基础）  

---

## 用户故事关联

| 用户故事 | 描述 |
|---------|------|
| US-01 | 挂载本地项目目录，Agent 对话时能感知代码库上下文 |
| US-02 | 通过「需求类型」告知 Agent 当前意图，不走无关阶段 |
| US-03 | 对话产物与项目绑定，下次打开可继续 |
| US-04 | 管理多个客户项目，快速切换上下文 |
| US-05 | 对话界面展示当前阶段、产物和下一步建议 |

---

## 本任务范围

> **纯静态实现**：所有数据使用 mock，不接后端 API。目的是验证交互体验是否符合预期，确认后再开启后端任务。

涵盖两个页面：

1. **项目管理页**（`/projects`）— 我的项目列表 + 创建项目向导
2. **Agent 对话页重构**（`/chat`）— 在现有 Chat UI 基础上叠加新的交互层

---

## 技术子项 Checklist

### 阶段 1：路由与页面骨架

- [ ] 在 `router/index.ts` 新增 `/projects` 路由
- [ ] 在 `AppSidebar.vue` 的 menuItems 中新增「项目」入口（图标：folder，位置：chat 之后）
- [ ] 新建目录 `views/projects/`
- [ ] 新建 `views/projects/Index.vue`（项目列表页骨架）
- [ ] 新建 `views/projects/Create.vue`（创建向导骨架）

### 阶段 2：项目列表页（`/projects`）

- [ ] **空状态**：无项目时展示引导卡片（图标 + 文案 + 「创建第一个项目」按钮）
- [ ] **项目卡片**：展示项目名称、技术栈标签、挂载状态（已连接 / 未连接）、最近活跃时间
- [ ] **挂载状态 badge**：绿点（已连接）/ 灰点（未连接）
- [ ] **卡片操作**：「继续对话」跳转 `/chat`，「项目设置」跳转设置面板
- [ ] **mock 数据**：2-3 个示例项目（含不同技术栈和挂载状态）
- [ ] **新建按钮**：右上角「+ 新建项目」触发创建向导

### 阶段 3：创建项目向导（`/projects/create`）

- [ ] **多步骤布局**：顶部步骤条（Step 1 基本信息 / Step 2 挂载代码库 / Step 3 技术栈标签）
- [ ] **Step 1 基本信息**：项目名称输入框 + 项目描述（可选）
- [ ] **Step 2 挂载代码库**：三种方式的选择卡片（本地目录 CLI / GitHub OAuth / 手动上传），每种卡片含图标、标题、说明文字；本地方式展示 CLI 命令代码块
- [ ] **Step 3 技术栈标签**：预设常用技术栈 tag 可点击选择（Vue 3 / React / FastAPI / Django / PostgreSQL / MySQL / Redis / Docker…），支持自定义输入；角色选择（主项目 / 参考项目 / 文档库）
- [ ] **Step 4 完成**：成功态展示，含「开始第一次对话」按钮
- [ ] **上一步 / 下一步**导航，最后一步变为「完成」
- [ ] **表单校验**：项目名称必填，其余可选

### 阶段 4：Agent 对话页 — 新增交互组件

在现有 `views/chat/Index.vue` 基础上，新增以下组件，**不破坏原有功能**：

#### 4.1 顶部项目选择栏

- [ ] 新建 `components/chat/ProjectBar.vue`
- [ ] 展示当前选中项目名称 + 技术栈（mock：「我的电商后端 · FastAPI · Vue 3」）
- [ ] 点击展开下拉，列出所有项目可切换（mock 数据）
- [ ] 「管理项目」链接跳转 `/projects`

#### 4.2 需求类型选择器（IntentSelector）

- [ ] 新建 `components/chat/IntentSelector.vue`
- [ ] 4 个模式按钮：全新功能 ✨ / 迭代优化 🔄 / UI 调整 🎨 / Bug 修复 🐛
- [ ] 激活态样式（高亮边框 + 浅色背景）
- [ ] 选中后触发 `emit('change', intent)`
- [ ] 默认选中「迭代优化」

#### 4.3 阶段预览条（StagePreview）

- [ ] 新建 `components/chat/StagePreview.vue`
- [ ] 接收 `intent` prop，根据类型展示对应阶段列表
- [ ] 阶段以 pill 形式展示，箭头连接
- [ ] 可选阶段打 `*` 标注
- [ ] 跳过的阶段以灰色小字在末尾展示「跳过：xxx」
- [ ] 阶段数据（4 种模式的阶段配置）抽成 `composables/usePipeline.ts` 常量

#### 4.4 上下文 Chips（ContextChips）

- [ ] 新建 `components/chat/ContextChips.vue`
- [ ] mock 数据：`[{ label: 'main 分支', active: true }, { label: 'PRD-CLAW.md', active: true }, { label: 'engine.py', active: false }]`
- [ ] chip 可点击切换激活 / 停用状态
- [ ] 「+ 添加上下文」按钮（静态，无交互）
- [ ] 激活态：紫色背景；停用态：灰色

#### 4.5 快捷动作栏（重构现有 QuickActions）

- [ ] 将现有 `quick-actions` 区域重构，接收 `intent` prop 动态切换内容
- [ ] 每个模式显示 3-4 个对应动作，一个高亮（高亮的自动 focus 提示）
- [ ] 动作点击仍调用 `fillPrompt()`，prompt 内容改为阶段感知版本
- [ ] 4 种模式的动作配置统一放入 `composables/usePipeline.ts`

#### 4.6 阶段完成通知卡片（StageCompleteCard）

- [ ] 新建 `components/chat/StageCompleteCard.vue`
- [ ] props：`stage`（阶段名）、`artifactName`（产物名）
- [ ] 展示：✅ 阶段完成 + 产物名 + 「查看」/ 「确认，进入下一阶段」/ 「我要修改」三个按钮
- [ ] 在 Chat 消息流中作为系统消息渲染（`role: 'system'`）
- [ ] **mock 演示**：在 WelcomeScreen 或消息区底部预置一条示例卡片

#### 4.7 人工确认卡片（ConfirmCard）

- [ ] 新建 `components/chat/ConfirmCard.vue`
- [ ] props：`title`、`checkItems`（待确认要点列表）、`nextStage`
- [ ] 展示：⏸ 标题 + checklist 要点 + 「确认，继续 xxx」/ 「我有修改意见」
- [ ] **mock 演示**：预置一条 PRD 确认示例

### 阶段 5：整体组装与走查

- [ ] 在 `views/chat/Index.vue` 中引入 `ProjectBar`、`IntentSelector`、`StagePreview`、`ContextChips`
- [ ] IntentSelector 的 `change` 事件联动 `StagePreview` 和 `QuickActions`
- [ ] 确认切换模式时 placeholder 文案同步变化（4 种模式各一句）
- [ ] 确认现有发送消息、流式回复、会话历史功能**不受影响**
- [ ] 移动端响应式：IntentSelector / StagePreview / ContextChips 在窄屏下折叠或简化展示

### 阶段 6：样式走查与细节打磨

- [ ] 与 PRD 原型图比对，确认整体布局符合预期
- [ ] 颜色与现有 variables.scss 对齐（主色 #409eff，文字层级，border 颜色）
- [ ] 各组件 hover / active / disabled 状态完整
- [ ] 无明显错位、截断、溢出问题
- [ ] 深色背景区域文字对比度达标

---

## 验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `/projects` 页面可访问，空状态引导卡片正常展示 | 浏览器访问 |
| 2 | 创建项目向导 3 步可走通，步骤条状态正确 | 手动操作 |
| 3 | Chat 页顶部项目栏展示 mock 项目信息 | 浏览器访问 |
| 4 | 需求类型选择器 4 个模式可切换，阶段预览条联动变化 | 手动切换 |
| 5 | 快捷动作栏随模式切换内容，高亮动作正确 | 手动切换 |
| 6 | 上下文 Chips 可点击切换激活状态 | 手动点击 |
| 7 | 阶段完成卡片和确认卡片在消息区正常渲染 | 浏览器查看 |
| 8 | 原有发送消息 / 流式回复 / 会话列表功能不受影响 | 发送一条消息验证 |
| 9 | 移动端（375px）下页面无横向滚动，核心功能可用 | DevTools 模拟 |

---

## 产出物

| 文件 | 说明 |
|------|------|
| `views/projects/Index.vue` | 项目列表页 |
| `views/projects/Create.vue` | 创建项目向导 |
| `components/chat/ProjectBar.vue` | 顶部项目选择栏 |
| `components/chat/IntentSelector.vue` | 需求类型选择器 |
| `components/chat/StagePreview.vue` | 阶段预览条 |
| `components/chat/ContextChips.vue` | 上下文 Chips |
| `components/chat/StageCompleteCard.vue` | 阶段完成通知卡片 |
| `components/chat/ConfirmCard.vue` | 人工确认卡片 |
| `composables/usePipeline.ts` | 流水线阶段配置 + 意图路由常量 |
| `router/index.ts` | 新增 `/projects`、`/projects/create` 路由 |
| `components/layout/AppSidebar.vue` | 新增「项目」导航入口 |

---

## 不在本任务范围内

- ❌ 后端 API（Project / Mount / Artifact 表和接口）
- ❌ Agent Bridge / CLI 工具实现
- ❌ 真实文件系统读取
- ❌ GitHub OAuth 集成
- ❌ 产物文件保存
- ❌ 阶段完成卡片的真实 SSE 事件接入

以上均在后续任务（TASK-008 及之后）实现。

---

## 备注

- 所有 mock 数据写在组件内部或 `composables/usePipeline.ts`，不引入新的 store
- 组件命名遵循现有项目规范（PascalCase，`<script setup lang="ts">`，`<style scoped lang="scss">`）
- 新组件的样式颜色值统一引用 `variables.scss` 中的变量，禁止写魔法数字颜色
