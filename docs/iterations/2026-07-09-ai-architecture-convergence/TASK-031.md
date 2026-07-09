# TASK-031: 第三方 Skill 导入与运行时闭环

```yaml
id: AIARCH-P1-005
module: skills
priority: P1
title: 第三方 Skill 导入与运行时闭环
related_requirements:
  - R-005
deliverable:
  - Skill Manifest parser
  - Skill import preview API
  - Skill permission policy
  - Runtime registry refresh
  - Skill audit tests
acceptance:
  - 第三方 Skill 安装前能展示来源、工具、权限和风险
  - 安装后能进入 SkillRegistry
  - 调用经过权限判断并写审计
status: done
```

## 背景

Skill 市场如果只展示“可安装”，长期会变成安全风险。真正可用的 Skill 市场必须有 Manifest、权限、运行时注册和审计闭环。

## 范围

- 支持从 GitHub URL / PyPI 包名 / 本地目录导入。
- 校验 `agentforge-skill.yaml` 或兼容格式。
- 安装前提供 preview。
- 权限声明包括 network、filesystem、shell、credential、project_context。
- 安装后刷新 SkillRegistry。
- 调用前经过 SkillPolicy。
- 调用后写审计和 Eval 事件。

## 实施 checklist

- [x] 梳理现有 `SkillInstaller` 和 `SkillLoader`。
- [x] 设计 Manifest schema。
- [x] 新增 Manifest parser 和 validator。
- [x] 新增 import preview API。
- [x] 安装流程记录 manifest_hash 和 permissions。
- [x] SkillRegistry 支持外部 Skill runtime spec。
- [x] SkillDispatcher 调用前执行权限校验。
- [x] 前端安装弹窗展示权限和风险。

## 完成说明

- 新增 `agentforge-skill.yaml` 优先、`skill.md` 兼容的 Manifest 解析与校验，统一生成 `SkillRuntimeSpec`、工具定义、权限声明、风险等级和 manifest hash。
- 新增 `/api/v1/skills/import/preview` 与 `/api/v1/skills/import/install`，安装前返回来源、工具、权限、风险和确认要求；高风险权限未确认时返回 409。
- `Skill` 与 `SkillInstall` 记录 `manifest_hash`、`permissions`、`runtime_spec`、`risk_level` 和安装预览快照，便于后续审计和复盘。
- `SkillRegistry` 保存 runtime spec 与 tool -> skill 映射，第三方本地 Skill 安装后会复制到 `skills/installed/` 并注册 executor。
- `SkillDispatcher` 调用前执行 `SkillPermissionPolicy`，权限拒绝会写入 `AuditLog` 并发出 `skill_eval` 事件；成功、失败、超时也会输出统一评估事件。
- 前端 Skill 安装弹窗增加导入预览、权限标签、风险提示和确认安装动作。
- PyPI/GitHub/Git 导入支持安装前预览；第三方归档预览采用安全解压，拒绝路径穿越和链接条目。

## 验收标准

- Manifest 缺失或字段非法时安装失败。
- 权限超出策略时安装失败或进入确认。
- 禁用 Skill 后运行时不可调用。
- 卸载 Skill 后 Registry 同步移除。
- 调用审计记录包含 skill_name、version、source、permission、status。

## 验证

```bash
uv run --extra dev pytest tests/api/test_skills.py tests/skills/test_dispatcher.py
```

```bash
uv run --extra dev pytest tests/api/test_skill_import.py
```

```bash
npm run build
```

前端命令在 `/Users/yangkl/AgentForge/web` 下执行。

## 后续边界

- `StageDefinition.skill_policy_key`、`AgentProfile.allowed_skill_names` 与统一策略编排留给 TASK-032。
- 结构化 `EvalEvent` 表和 Dashboard 级统计留给 TASK-033；本任务先通过 `skill_eval` SSE / callback 事件和审计日志保留事实。
