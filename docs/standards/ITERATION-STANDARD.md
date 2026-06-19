# 迭代执行规范

## 1. 目标

每次迭代都先完成任务拆分和验收设计，再进入具体实现。任务按模块和优先级组织，执行时保持小步完成、小步验证、小步提交。

## 2. 迭代目录

新迭代统一放在：

```text
docs/iterations/YYYY-MM-DD-topic/
```

目录名使用日期加主题，主题使用小写英文或拼音短语，避免空格。

## 3. 标准产物

```text
PRODUCT-REQUIREMENTS.md  # 产品需求：为什么做、做什么、不做什么
TASK-CHECKLIST.md        # 任务拆分：模块、优先级、产出物、验收标准、完成状态
TECHNICAL-DESIGN.md      # 技术设计：架构、模块边界、接口、数据流、错误处理
UI-DESIGN.md             # UI/UX 设计：页面结构、交互、视觉系统；仅 UI 相关迭代需要
TEST-PLAN.md             # 测试与验收：验证方式、测试用例、手工验收点
ITERATION-REVIEW.md      # 迭代复盘：完成情况、决策、遗留问题
```

不要使用 `DESIGN.md` 这类泛名。技术设计、产品设计、UI 设计必须写全，避免人和 Agent 误读。

## 4. Task 与 Checklist 关系

`TASK-CHECKLIST.md` 只做任务索引，不堆技术细节。每个可执行任务必须拆成独立任务文件：

```text
TASK-001.md
TASK-002.md
TASK-003.md
```

推荐关系：

```text
PRODUCT-REQUIREMENTS.md
  -> 用户故事
    -> TASK-NNN.md
      -> 技术子项 checklist
      -> 验收标准
      -> 产出物
```

`TASK-CHECKLIST.md` 至少维护：

- 用户故事覆盖矩阵
- 任务索引
- 任务优先级
- 任务依赖关系
- 任务级完成状态

每个 `TASK-NNN.md` 至少包含：

- `id`：稳定编号，例如 `ARCH-P0-001`
- `module`：所属模块
- `priority`：`P0`、`P1`、`P2`、`P3`
- `title`：任务标题
- `related_requirements`：关联的用户故事或产品需求点
- `deliverable`：产出物
- `acceptance`：验收标准
- `status`：`todo`、`doing`、`done`

推荐格式：

```yaml
- id: ARCH-P0-001
  module: architecture
  priority: P0
  title: 明确 MVP 架构边界
  related_requirements:
    - US-1
    - US-2
  deliverable: TECHNICAL-DESIGN.md
  acceptance:
    - 明确第一阶段包含和不包含的能力
    - 明确核心执行链路
  status: todo
```

## 5. 执行与提交节奏

- 完成 1 个 checklist item 后，立即把该项状态更新为 `done`。
- 每完成 1 个 checklist item，单独 commit 一次。
- commit 内容只包含该 checklist item 相关文件。
- 如果一个 item 太大，先拆小再执行。

## 6. 本地 UI/UX Skill 策略

前端 UI/UX 相关任务允许使用本地已安装的 `ui-ux-pro-max` skill：

```text
~/.claude/skills/ui-ux-pro-max
```

该 skill 来源：

```yaml
id: ui-ux-pro-max
local_path: ~/.claude/skills/ui-ux-pro-max
upstream_repo: nextlevelbuilder/ui-ux-pro-max-skill
install_scope: local_user
dynamic_download: false
skill_type: advisory
```

允许任务类型：

```yaml
allowed_task_types:
  - ui.design
  - ui.review
  - ux.flow
  - design_system.generate
  - frontend.visual_spec
```

禁止任务类型：

```yaml
forbidden_task_types:
  - backend.*
  - database.*
  - security.*
  - deployment.*
  - agent_orchestration.*
  - core_domain_model.*
```

使用要求：

- 仅作为 advisory skill 使用，不直接决定系统架构。
- 输出必须沉淀到 `UI-DESIGN.md` 或 `UI-REVIEW.md`。
- 重要 UI 迭代需要记录使用时的本地 skill 状态或版本来源。
- 不在迭代执行中动态下载或自动更新该 skill。
- 该 skill 是开发过程辅助能力，不默认注册到 AgentForge 产品运行时的 SkillRegistry。

## 7. UI 输出约束

AgentForge 是开发者和 Agent 编排平台。使用 UI/UX skill 时，输出应偏向：

- 操作型界面
- 信息密度适中
- 专业、克制、可扫描
- 可访问性优先
- 适合长期使用的管理后台体验

应避免：

- 营销落地页式表达
- 过度装饰
- 低密度卡片堆叠
- 不服务任务效率的视觉效果
- 由视觉风格反向决定业务和技术架构
