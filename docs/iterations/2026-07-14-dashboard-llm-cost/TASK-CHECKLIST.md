# TASK-046 任务清单

- [x] 明确 Evaluation 单一事实源、用户隔离和非流式 usage 范围。
- [x] 用红灯测试刻画 Evaluation 缺少 LLM ModelRoute / Stage 专属聚合。
- [x] 用红灯测试复现 `evaluation_context` 与 Engine `eval` 键名错位。
- [x] 用红灯测试刻画 Dashboard API 缺少 `evaluation.llm` 契约。
- [x] 实现 LLM 维度聚合、规范 evaluation context 和 Stage 名称透传。
- [x] 实现 Dashboard schema 映射。
- [x] 建立 Dashboard LLM 总览、排行和零数据浏览器 E2E 契约。
- [x] 实现 Dashboard LLM 成本、Token、延迟和排行界面。
- [x] 同步 API、架构上下文、文档索引和迭代复盘。
- [x] 完成相关回归、后端全量、前端构建和 FastAPI 生命周期验证。
- [x] 记录 sandbox 无法绑定本地端口导致 Dashboard E2E 未执行的环境豁免。
- [ ] 中文提交并推送功能分支，合并并推送 `main`。
