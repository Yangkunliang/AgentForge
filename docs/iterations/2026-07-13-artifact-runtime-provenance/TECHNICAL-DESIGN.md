# TASK-044 技术设计：Artifact runtime provenance

## 设计取舍

本任务不新增 Artifact 表字段，而是复用现有 `Artifact.metadata_json`，在 StageRuntime 生成的产物中增加稳定的 `runtime` 子对象。这样能立即被 Artifact API、Viewer、导出和后续 Eval 分析消费，同时避免一次小任务引入迁移成本。

## Metadata 契约

```json
{
  "runtime": {
    "agent_profile": {
      "id": "system-default",
      "name": "CodeSoul",
      "source": "system_default"
    },
    "model_route": {
      "route_key": "default",
      "name": "Legacy Settings",
      "source": "legacy_settings"
    },
    "model_name": "openai/deepseek-v4-pro",
    "skill_policy_key": "default"
  }
}
```

只保存可展示、可追溯、无密钥的信息；Credential id/name、API Key、prompt、上下文文件内容不进入 Artifact metadata。

## 代码改动

- `src/agent_forge/artifacts/service.py`
  - `create_stage_artifact()` 支持 `runtime_metadata`。
  - `build_stage_runtime_metadata()` 从 `PipelineStageState` 构造非敏感来源。
- `src/agent_forge/pipeline/runtime.py`
  - `_complete_stage()` 将当前 `skill_policy_key` 和 stage 上已解析的 agent/model 字段写入 Artifact。
- `web/src/views/artifacts/Detail.vue`
  - 从 `artifact.metadata.runtime` 读取并展示 Agent、模型和路由。

## 风险控制

- metadata 是兼容性扩展，手动创建 Artifact 的 API 请求无需变更。
- 前端仅在字段存在时展示，不影响历史产物。
- 测试断言不绑定本地默认模型名，避免不同环境配置导致误报。
