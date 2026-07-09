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
status: todo
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

- 梳理现有 `SkillInstaller` 和 `SkillLoader`。
- 设计 Manifest schema。
- 新增 Manifest parser 和 validator。
- 新增 import preview API。
- 安装流程记录 manifest_hash 和 permissions。
- SkillRegistry 支持外部 Skill runtime spec。
- SkillDispatcher 调用前执行权限校验。
- 前端安装弹窗展示权限和风险。

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
