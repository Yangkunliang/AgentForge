# Skill Engine — 任务清单

**迭代版本**：2026-06-22-skill-engine

## 阶段 0：数据库 Migration

| # | 任务 | 状态 |
|---|------|------|
| 0.1 | 新增 `002_skill_engine.py` migration（skills/agent_skills 扩展字段） | ✅ |

## 阶段 1：Skill 执行引擎（解决捏造问题）

| # | 任务 | 状态 |
|---|------|------|
| 1.1 | 实现 `weather.py`（Open-Meteo 天气 Skill） | ✅ |
| 1.2 | 实现 `registry.py`（SkillRegistry 运行时缓存） | ✅ |
| 1.3 | 实现 `dispatcher.py`（SkillDispatcher 路由执行） | ✅ |
| 1.4 | 实现 `engine.py`（SkillExecutionEngine ReAct 循环） | ✅ |
| 1.5 | 修改 `sessions.py`：`_run_task_with_skills` 替换原函数 | ✅ |
| 1.6 | 修改 `builtin.py`：注册天气 Skill | ✅ |
| 1.7 | 修改 `main.py`：启动时初始化 SkillRegistry | ✅ |

## 阶段 2：Skill 市场

| # | 任务 | 状态 |
|---|------|------|
| 2.1 | 补充 `skills.py` marketplace 端点（GitHub Topic 查询） | ✅ |
| 2.2 | 补充 enable/disable 端点 | ✅ |
| 2.3 | 前端 marketplace UI 补全（GitHub 真实数据） | ✅ |

## 阶段 3：前端完善

| # | 任务 | 状态 |
|---|------|------|
| 3.1 | `skills.ts` API 补充 marketplace search / enable / disable | ✅ |
| 3.2 | `skill.ts` store 补充 marketplace 状态 | ✅ |
| 3.3 | `List.vue` 补充 marketplace tab + enable/disable 操作 | ✅ |

## 验收标准

- ✅ 问天气返回 Open-Meteo 真实数据，不再捏造
- ✅ 问搜索相关问题返回 DuckDuckGo 真实结果
- ✅ ReAct 循环最多 5 轮，有超时保护
- ✅ Skill 安装支持 GitHub URL / PyPI / 本地
- ✅ 市场页面能显示 GitHub 真实 Skill 列表
