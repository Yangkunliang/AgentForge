# TASK-018：Agent Bridge / 真实代码库读取

**状态**：todo
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

- [ ] 设计 `agentforge mount <path>` CLI MVP
- [ ] Bridge 进程记录 mount_id、project_id、root_path
- [ ] 后端 Bridge 状态 API
- [ ] 前端展示 Mount 连接状态
- [ ] 文件读取 API 只允许访问授权 root 内路径
- [ ] ContextPicker 支持从授权 Mount 选择文件
- [ ] SkillExecutionEngine 需要文件内容时调用 Bridge read tool
- [ ] 安全文档补充路径穿越、敏感文件和权限边界

## acceptance

- [ ] 用户手动 mount 后项目显示 connected
- [ ] Agent 只能读取授权目录内文件
- [ ] 同名文件展示完整相对路径
- [ ] Bridge 断开后前端状态变为 disconnected
- [ ] 路径穿越测试必须被拒绝
- [ ] `uv run --extra dev pytest` 通过

## 不做

- 不自动扫描用户本机目录。
- 不做桌面客户端。
- 不做 GitHub OAuth。
