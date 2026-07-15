# 核心迭代工作流执行链任务清单

按优先级和依赖顺序推进；每项独立分支、独立验证、合并并推送 `main` 后再开始下一项。

- [x] TASK-047：StageExecutionContext，把阶段定义、输入要求、完成标准和上游 Artifact 接入真实执行提示。
- [ ] TASK-048：Dashboard 多租户隔离，修复 Task 数量、费用和最近任务跨用户读取风险。
- [ ] TASK-049：TaskGraph，把任务拆解产物升级为结构化、可依赖、可执行、可验收的任务图。
- [ ] TASK-050：WorkspaceExecutor，在用户授权 ProjectMount 内生成、预览和应用文件级 Patch。
- [ ] TASK-051：VerificationGate，执行真实测试/构建命令，以结构化结果阻断失败交付。
- [ ] TASK-052：PipelineOrchestrator，统一确认后推进、下一阶段启动、Run 完成和新需求生命周期。
- [ ] TASK-053：全链路 E2E 与交互收敛，覆盖需求分析到交付的浏览器验收、失败恢复和运行观测。
