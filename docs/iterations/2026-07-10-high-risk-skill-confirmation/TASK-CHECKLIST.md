# TASK-039 Checklist

## Checklist

- [x] 梳理 chat 请求、SSE、StageRuntime 和前端消息区接入点。
- [x] 补 `ChatRequest` 授权上下文红灯测试。
- [x] 补 StageRuntime 授权请求 SSE 红灯测试。
- [x] 后端支持 `skill_authorization` chat payload。
- [x] StageRuntime 在高风险 Skill 被过滤时发出 `skill_authorization_required`。
- [x] 前端 `useChat` 监听授权请求并保存一次性重试上下文。
- [x] 前端新增 `SkillAuthorizationCard`，支持授权重试和忽略。
- [x] 同步 API、架构、安全、前端和迭代文档。

## 后续

- 将授权请求与 ConfirmCard 做更深的阶段级合流。
- 将授权事实写入 EvalEvent，观察用户授权频率和授权后成功率。
