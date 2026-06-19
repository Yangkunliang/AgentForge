# TASK-004：Skill 插件系统 & 辅助 API

## 关联需求

| 用户故事 | 描述 |
|---------|------|
| US-3 | 作为全栈开发者，我想快速导入新的 Skill 插件，扩展 Agent 能力 |
| US-4 | 作为全栈开发者，我想导出训练数据，优化我的模型和 Agent 路由 |
| US-5 | 作为全栈开发者，我想看到安全的 API 调用记录，以便审计和合规 |

## 优先级

**P2** — 依赖 TASK-001 + TASK-003，完善框架功能完整度

## 验收标准

- [ ] `POST /skills/install` 能异步安装 Skill，返回 install_id
- [ ] `GET /skills/install/{id}` 轮询返回 installing/done/failed + 日志
- [ ] 安装完成后 Skill 自动注册到 SkillRegistry，可被 Agent 调用
- [ ] `GET /dashboard` 返回任务统计、Agent 状态、费用趋势正确
- [ ] `POST /exports` 能生成 JSONL 文件，PII 字段已脱敏
- [ ] Webhook 回调：任务完成后正确触发，签名可验证

## 技术子项

### Skill 插件系统（`src/agent_forge/skills/`）

- [ ] **SkillLoader**（`loader.py`）
  - 异步执行 `pip install <source>`（subprocess + asyncio）
  - 实时追加安装日志到 Redis key（`skill:install:{install_id}:log`）
  - 安装完成后自动注册到 SkillRegistry

- [ ] **SkillManager**（`manager.py`）
  - 加载：读取 `skill.md`（LLM 指令）+ 动态导入 `executor.py`
  - 调用：`execute(skill_name, input) → result`
  - 卸载：从 Registry 移除 + `pip uninstall`

- [ ] **Skill API**（`src/api/routes/skills.py`）
  - `POST /api/v1/skills/install`（需 admin 权限）→ 返回 `{ install_id, skill_name, status }`
  - `GET /api/v1/skills/install/{install_id}` → 返回 `{ status, log, error }`
  - `GET /api/v1/skills` → 已安装列表
  - `DELETE /api/v1/skills/{skill_name}`（需 admin 权限）

### Dashboard + Cost API（`src/api/routes/dashboard.py`）

- [ ] `GET /api/v1/dashboard`
  - 聚合查询：Task 状态分布（今日）、Agent active/inactive 数、Skill 总数
  - 费用：today_usd、trend_pct（对比昨日）、daily_7d（近 7 天每日合计）
  - 最近 5 条任务（recent_tasks）
  - 参考：`docs/tech-design/API-SPEC.md` 第 6 节

- [ ] `GET /api/v1/cost`
  - 按日 + 按模型明细（从 TaskExecution 表聚合）
  - 参考：`docs/tech-design/API-SPEC.md` 第 7 节

### 数据导出（`src/api/routes/exports.py` + `src/agent_forge/exporter/`）

- [ ] `POST /api/v1/exports`（需 admin 权限）
  - 异步生成 JSONL，返回 export_id
  - 支持时间范围、导出类型（training_data）、脱敏级别

- [ ] `GET /api/v1/exports/{export_id}` — 查询导出状态

- [ ] `GET /api/v1/exports/{export_id}/download` — 下载文件

- [ ] **PII 脱敏**（`src/agent_forge/exporter/sanitizer.py`）
  - 邮箱：保留域名（`u***@example.com`）
  - 手机号：保留后 4 位（`138****1234`）
  - 参考：`docs/tech-design/DATA-EXPORT.md`

### Webhook 回调（`src/api/routes/webhooks.py`）

- [ ] `POST /api/v1/webhooks` — 注册回调 URL + 事件类型，返回签名密钥
- [ ] 任务完成/失败时触发回调（httpx async POST）
- [ ] HMAC-SHA256 签名写入 `X-Signature` Header

## 产出物

- `src/agent_forge/skills/loader.py` + `manager.py`
- `src/api/routes/skills.py`
- `src/api/routes/dashboard.py`
- `src/api/routes/exports.py`
- `src/agent_forge/exporter/sanitizer.py` + `generator.py`
- `src/api/routes/webhooks.py`

## 参考文档

- `docs/tech-design/API-SPEC.md` 第 5-10 节
- `docs/tech-design/DATA-EXPORT.md`
- `docs/product-design/PRD-多智能体框架-20260617.md` US-3、US-4、US-5
