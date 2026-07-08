# TASK-018：Agent Bridge / 真实代码库读取

**状态**：done
**优先级**：P1
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-DEV-WORKFLOW
**依赖**：TASK-013、TASK-017

## 目标

实现用户主动授权的本地代码库读取能力，让 Agent 能基于真实文件内容回答、分析影响范围和生成产物。

## related_requirements

- CDW-02：主动授权代码库上下文
- CDW-06：读取真实代码库

## 技术子项

- [x] 设计 `agentforge mount <path>` CLI MVP
- [x] Bridge 记录 mount_id、project_id、root_path
- [x] 后端 Bridge 状态 API
- [x] 前端展示 Mount 连接状态
- [x] 文件读取 API 只允许访问授权 root 内路径
- [x] ContextPicker 支持从授权 Mount 选择文件
- [x] 选中文件在 Chat 请求进入 SkillExecutionEngine 前被读取并注入上下文
- [x] 安全文档补充路径穿越、敏感文件和权限边界

## acceptance

- [x] 用户手动 mount 后项目显示 connected
- [x] Agent 只能读取授权目录内文件
- [x] 同名文件展示完整相对路径
- [x] Bridge 断开后前端状态变为 disconnected
- [x] 路径穿越测试必须被拒绝
- [x] `uv run --extra dev pytest` 通过

## 实现摘要

- 新增 `agentforge mount <path>` CLI 入口，创建 connected local ProjectMount，并在 metadata 记录 `root_path` 与 `bridge=agentforge-cli`。
- 新增 Bridge 文件访问层 `agent_forge.bridge.files`，统一处理根目录校验、路径穿越拒绝、敏感文件拒绝、常见依赖/构建目录过滤和 UTF-8 文本读取。
- 新增后端 API：`GET /projects/{project_id}/bridge/status`、`GET /projects/{project_id}/mounts/{mount_id}/files`、`POST /projects/{project_id}/mounts/{mount_id}/files/read`。
- Chat `context_files[type=file]` 支持 `mount_id`；带 `mount_id` 的文件会在发送消息时读取真实内容，并注入 `SkillExecutionEngine` system prompt。
- 前端 `ContextPickerDialog` 可浏览当前项目 connected local mount 的文件，选中文件后 chip 显示 `MountName/完整相对路径`，聊天 payload 携带 `mount_id`。

## 验证

- `uv run --extra dev pytest tests/api/test_projects.py tests/api/test_bridge_cli.py tests/skills/test_engine_context.py`
- `npm run build`
- `npm run test:e2e -- bridge-context.spec.ts`

## 不做

- 不自动扫描用户本机目录。
- 不做桌面客户端。
- 不做 GitHub OAuth。
