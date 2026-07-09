# TASK-028: Pipeline Stage Catalog 后端唯一事实源

```yaml
id: AIARCH-P0-002
module: pipeline
priority: P0
title: Pipeline Stage Catalog 后端唯一事实源
related_requirements:
  - R-002
deliverable:
  - src/agent_forge/pipeline/catalog.py
  - src/api/routes/pipeline_catalog.py
  - web/src/api/modules/pipelineCatalog.ts
  - tests/api/test_pipeline_catalog.py
acceptance:
  - 后端能按 intent_type 返回阶段定义
  - StageRuntime 使用后端 StageDefinition
  - 前端核心阶段展示从 API 读取，不重复维护业务事实源
status: todo
```

## 背景

Pipeline 是 AgentForge 的主干。如果阶段语义散落在前端常量、后端配置和运行时代码中，后续新增需求类型会不断变慢。

## 范围

- 建立后端 Pipeline Catalog。
- 为每个 intent type 返回阶段定义、确认策略、输出物类型和默认动作。
- 前端 Pipeline Store / StagePreview 消费后端 catalog。

## 实施 checklist

- 梳理现有 `src/agent_forge/pipeline/config.py` 中的阶段配置。
- 设计 `StageDefinition` 数据结构。
- 新增 Pipeline Catalog Service。
- 新增 catalog API。
- 修改 StageRuntime 获取阶段定义的方式。
- 修改前端 API 和 Store。
- 保留旧配置兜底，避免旧会话立刻不可用。

## 验收标准

- 新功能、迭代优化、UI 调整、Bug / 重构四类需求能返回不同阶段组合。
- 阶段是否可跳过、是否需要确认、输出什么 Artifact，由后端返回。
- 前端构建通过。

## 验证

```bash
uv run --extra dev pytest tests/api/test_pipeline_runs.py tests/pipeline/test_runtime.py
```

```bash
uv run --extra dev pytest tests/api/test_pipeline_catalog.py
```

```bash
npm run build
```

前端命令在 `/Users/yangkl/AgentForge/web` 下执行。
