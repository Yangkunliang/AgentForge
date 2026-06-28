# TASK-011：高级设置面板功能实现

## 关联需求

PRD 截图中的「高级设置」面板，包含四个功能区：
- 需求类型（IntentSelector）
- 上下文（ContextChips）
- 执行阶段（StagePreview）
- 快捷动作（QuickActions）

目标：让这四个模块真正协同工作，状态持久化，并在发送消息时将配置注入后端。

---

## 现状分析

| 模块 | 文件 | 现状 |
|---|---|---|
| IntentSelector | `components/chat/IntentSelector.vue` | 基本可用，emit v-model，但状态只在 Index.vue 局部 ref |
| ContextChips | `components/chat/ContextChips.vue` | 纯静态硬编码，无持久化，无真实文件选择逻辑 |
| StagePreview | `components/chat/StagePreview.vue` | 只读展示，阶段不可点击跳过，不响应用户修改 |
| QuickActions | `views/chat/Index.vue` 内联 | 已能 fillPrompt，但与 intent 联动依赖 `currentConfig`，逻辑散落在 Index.vue |
| 状态层 | 无专属 store | `currentIntent` 是 Index.vue 局部 ref，刷新即丢 |

---

## 技术方案

### 一、新增 Pinia Store：`useAdvancedSettings`

**文件：** `web/src/stores/advancedSettings.ts`

```ts
// 核心状态结构
interface AdvancedSettingsState {
  intent: IntentType                    // 当前需求类型
  contextFiles: ContextFile[]           // 上下文文件列表
  stageOverrides: Record<string, boolean> // 阶段是否启用（key: stage.id）
  // 不存快捷动作——它由 intent 决定，从 usePipeline 派生
}

interface ContextFile {
  id: string          // uuid
  type: 'branch' | 'file' | 'url'
  label: string       // 展示名，如 "main 分支" / "engine.py"
  value: string       // 实际值，分支名 / 文件路径 / URL
  active: boolean     // 是否激活（灰色 = 关闭但保留）
}
```

**持久化：** 用 Pinia plugin 或手动 `watch` 写入 `localStorage('agentforge:advanced-settings')`，页面初始化时读取恢复。

**派生计算：**
```ts
// 当前生效的 contextFiles（仅 active=true 的）
const activeContextFiles = computed(() =>
  state.contextFiles.filter(f => f.active)
)

// 当前生效的 stages（基于 intent 推荐 + stageOverrides 覆盖）
const activeStages = computed(() => {
  const base = getConfig(state.intent).stages
  return base.filter(s => {
    // 用户未覆盖 → 取默认值（optional 默认 true，必需默认 true）
    return state.stageOverrides[s.id] ?? true
  })
})

// 发送时注入的 payload 参数
const chatPayload = computed(() => ({
  intent: state.intent,
  context_files: activeContextFiles.value.map(f => ({ type: f.type, value: f.value })),
  stage_overrides: Object.fromEntries(
    Object.entries(state.stageOverrides).filter(([, v]) => !v)  // 只传被关闭的
  ),
}))
```

---

### 二、改造 ContextChips

**目标：** 真实的上下文文件管理，支持增删改激活状态。

#### 2.1 交互设计

- Chip 默认显示 active 状态（蓝色边框 + 勾图标）
- 点击 Chip → 切换 `active`（变灰但不删除，方便再次开启）
- 长按 / 右键 → 弹出小菜单：「激活」「停用」「删除」
- 「+ 添加上下文」按钮 → 打开 `ContextPickerDialog`

#### 2.2 新增 ContextPickerDialog 组件

**文件：** `components/chat/ContextPickerDialog.vue`

三种上下文类型，UI 用 Tab 切换：

| Tab | 类型 | 输入方式 |
|---|---|---|
| 分支 | `branch` | 下拉选择或手动输入分支名 |
| 文件 | `file` | 文件路径输入（暂不接文件树，MVP 手动输入）|
| 网址 | `url` | URL 输入 + 基本格式校验 |

确认后 dispatch `advancedSettings.addContextFile()`。

#### 2.3 store actions

```ts
addContextFile(file: Omit<ContextFile, 'id'>) {
  // 去重：相同 type+value 不重复添加
  if (state.contextFiles.some(f => f.type === file.type && f.value === file.value)) return
  state.contextFiles.push({ ...file, id: crypto.randomUUID() })
}

toggleContextFile(id: string) {
  const f = state.contextFiles.find(f => f.id === id)
  if (f) f.active = !f.active
}

removeContextFile(id: string) {
  state.contextFiles = state.contextFiles.filter(f => f.id !== id)
}
```

---

### 三、改造 StagePreview（可交互阶段列表）

**目标：** optional 阶段可点击跳过/恢复，必需阶段不可关闭，视觉上区分三种状态。

#### 3.1 三种视觉状态

| 状态 | 触发条件 | 样式 |
|---|---|---|
| `active` | 必需阶段 或 optional 且未被跳过 | 白底黑字，实线边框 |
| `optional-active` | optional 且当前开启 | 黄底棕字（`#fef3c7` / `#b45309`），显示 `*` |
| `skipped` | optional 且用户点击跳过 | 灰底删除线，半透明 |

#### 3.2 交互

点击 optional 阶段 → 调用 `advancedSettings.toggleStage(stageId)`：
```ts
toggleStage(stageId: string) {
  const current = state.stageOverrides[stageId] ?? true
  state.stageOverrides[stageId] = !current
}
```

必需阶段不可点击（pointer-events: none），tooltip 提示「此阶段为必需步骤」。

#### 3.3 切换 intent 后重置

当 `intent` 变更时，清空 `stageOverrides`（重新从默认值开始），避免上一个 intent 的覆盖状态污染新 intent。

```ts
watch(() => state.intent, () => {
  state.stageOverrides = {}
})
```

---

### 四、QuickActions 整合

QuickActions 当前逻辑已经正确（由 intent → usePipeline → currentConfig.quickActions 派生），主要工作是：

1. 从 Index.vue 内联代码迁移到独立组件 `components/chat/QuickActions.vue`
2. props 接收 `actions`，emit `select(prompt: string)`
3. highlighted 动作蓝色背景，其余默认灰色

无需改造核心逻辑。

---

### 五、发送时注入高级设置参数

**修改文件：** `views/chat/Index.vue` → `send()` 函数
**修改文件：** `composables/useChat.ts` → `sendMessage()`
**修改文件：** `api/modules/sessions.ts` → `chat()` 请求参数

#### 5.1 前端改动

```ts
// Index.vue send()
async function send() {
  // ... 原有逻辑 ...
  const advSettings = useAdvancedSettingsStore()
  _send(finalContent, sessionId.value, advSettings.chatPayload)
}

// useChat.ts sendMessage() 签名扩展
async function sendMessage(
  content: string,
  id?: string,
  advancedPayload?: ChatAdvancedPayload,  // 新增
): Promise<AbortController | null>

// sessions.ts chat() 参数扩展
chat(sessionId: string, content: string, advanced?: ChatAdvancedPayload) {
  return request.post(`/sessions/${sessionId}/chat`, {
    content,
    ...advanced,
  })
}
```

#### 5.2 后端接口扩展（`POST /sessions/{id}/chat`）

新增可选字段，后端不强制校验，有值时透传给 Agent：

```python
class ChatRequest(BaseModel):
    content: str
    intent: str | None = None                    # 需求类型
    context_files: list[ContextFileItem] | None = None  # 上下文文件
    stage_overrides: dict[str, bool] | None = None      # 阶段覆盖

class ContextFileItem(BaseModel):
    type: Literal['branch', 'file', 'url']
    value: str
```

透传方式：将 `intent` / `context_files` 拼入 system prompt 或作为 `extra_context` 字段追加给 LLM。MVP 阶段只做透传，不做 Agent 侧的深度路由优化。

---

### 六、intent 联动自动推荐阶段

当用户选择新的 intent 时，`StagePreview` 自动更新为该 intent 的推荐阶段列表（从 `usePipeline.getConfig()` 读取），`stageOverrides` 清空。

视觉上可加一个短暂的「高亮过渡」动画（stage-pill 0.2s background transition），让用户感知到阶段已更新。

intent → 阶段联动关系（来自 usePipeline 现有配置）：

| Intent | 执行阶段 |
|---|---|
| 全新功能 | 需求分析 → 架构设计 → DB&API → 任务拆解 → UI原型 → 后端 → 前端 → 测试 |
| 迭代优化 | 需求Diff → 影响评估* → 后端 → 前端* → 回归测试 |
| UI 调整 | 原型Diff → 前端开发 → 视觉验收 |
| Bug 修复 | 问题定位 → 影响范围 → 修复 → 回归测试 |

（* = optional，可跳过）

---

## 文件产出物

| 新建 | 路径 |
|---|---|
| 新增 store | `web/src/stores/advancedSettings.ts` |
| 新增对话框 | `web/src/components/chat/ContextPickerDialog.vue` |
| 新增组件 | `web/src/components/chat/QuickActions.vue` |

| 改造 | 路径 | 改动重点 |
|---|---|---|
| ContextChips | `components/chat/ContextChips.vue` | 接入 store，支持增删激活 |
| StagePreview | `components/chat/StagePreview.vue` | optional 阶段可点击跳过 |
| IntentSelector | `components/chat/IntentSelector.vue` | 改为直接写 store（不再 emit v-model）|
| Index.vue | `views/chat/Index.vue` | 移除局部 intent ref，接入 store；send() 注入 payload |
| useChat.ts | `composables/useChat.ts` | sendMessage 新增 advancedPayload 参数 |
| sessions.ts | `api/modules/sessions.ts` | chat() 参数扩展 |
| types/index.ts | `types/index.ts` | 新增 ContextFile、ChatAdvancedPayload 类型 |

| 后端 | 路径 | 改动重点 |
|---|---|---|
| chat 路由 | `src/agent_forge/api/routes/sessions.py` | ChatRequest 新增可选字段 |
| engine | `src/agent_forge/engine.py` | 将 intent/context_files 拼入 system prompt |

---

## 实现顺序

```
Step 1：新增 types（ContextFile、ChatAdvancedPayload）
Step 2：新增 useAdvancedSettings store（含 localStorage 持久化）
Step 3：改造 IntentSelector → 接入 store
Step 4：改造 StagePreview → optional 可切换
Step 5：改造 ContextChips + 新增 ContextPickerDialog
Step 6：提取 QuickActions 为独立组件
Step 7：Index.vue 清理局部状态，全部接入 store
Step 8：useChat.ts + sessions.ts 扩展参数透传
Step 9：后端 ChatRequest + engine.py system prompt 注入
Step 10：端到端联调验收
```

---

## 验收标准

- [ ] 选择不同 intent 后，执行阶段自动更新，stageOverrides 清空
- [ ] optional 阶段点击后变为删除线灰色；再次点击恢复
- [ ] 添加上下文文件后，Chip 正确显示；点击可切换激活状态；支持删除
- [ ] 刷新页面后，intent / contextFiles / stageOverrides 保持上次状态
- [ ] 发送消息时，Network 请求体包含 `intent`、`context_files`、`stage_overrides` 字段
- [ ] 后端日志显示 intent 已注入 system prompt
- [ ] 快捷动作随 intent 切换联动更新

---

## 暂不做（MVP 边界）

- 上下文文件树浏览器（文件选择只做手动输入路径）
- 分支下拉（只做手动输入分支名）
- Agent 侧基于 intent 做路由优化（只做 system prompt 透传）
- 多 stageOverrides 预设保存（"我的常用配置"）
