# StageExecutionContext Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让真实 StageRuntime 按 Catalog 契约消费前序 Artifact，并把可信阶段指令与不可信产物内容分层传给 SkillExecutionEngine。

**Architecture:** Pipeline Catalog 定义阶段输入、输出和完成标准；独立 execution context loader 负责用户已校验 Run 内的 Artifact 过滤与截断；StageRuntime 只做组装，Engine 只做 prompt 分层。Artifact 类型继续由 Catalog 负责，删除第二套阶段映射。

**Tech Stack:** Python 3.14、FastAPI、SQLAlchemy async、pytest、dataclass。

## Global Constraints

- 不新增数据库表或迁移。
- 上游 Artifact 最多 6 个，单项 4000 字符，总计 12000 字符。
- Artifact 内容不得进入 system prompt。
- 每个生产代码行为必须先有失败测试。
- 每个 Task 完成后使用中文提交信息单独提交。

---

### Task 1: Pipeline Catalog 输入与完成标准

**Files:**
- Modify: `src/agent_forge/pipeline/catalog.py`
- Modify: `tests/api/test_pipeline_catalog.py`

**Interfaces:**
- Produces: `StageDefinition.required_input_artifact_types`、`StageDefinition.success_criteria` 和对应 Catalog API 字段。

- [x] **Step 1: 写 Catalog 红灯测试**

  ```python
  response = async_client.get("/api/v1/pipeline/catalog")
  stage_by_id = {
      stage["stage_id"]: stage
      for stage in next(item for item in response.json() if item["intent_type"] == "new_feature")["stages"]
  }
  assert stage_by_id["design"]["required_input_artifact_types"] == ["prd"]
  assert stage_by_id["backend_dev"]["success_criteria"] == [
      "实现后端与自动化测试。",
      "说明改动文件和回归结果。",
  ]
  ```

- [x] **Step 2: 运行红灯测试**

  Run: `uv run --extra dev pytest -q tests/api/test_pipeline_catalog.py`

  Expected: FAIL，响应缺少新字段。

- [x] **Step 3: 实现 StageDefinition 字段和所有阶段契约**

  ```python
  @dataclass(frozen=True)
  class StageDefinition:
      stage_id: str
      stage_name: str
      description: str = ""
      required: bool = True
      confirmation_required: bool = False
      confirmation_gate: str | None = None
      required_input_artifact_types: tuple[str, ...] = ()
      output_artifact_types: tuple[str, ...] = ("report",)
      success_criteria: tuple[str, ...] = ()
      default_agent_selector: str = "planner"
      model_route_key: str = "default"
      skill_policy_key: str = "default"
  ```

  `stage_definition_to_dict()` 增加两个 list 字段；阶段取值逐项使用 `TECHNICAL-DESIGN.md` 的阶段契约表，不自行扩展。

- [x] **Step 4: 运行 Catalog 测试并提交**

  Run: `uv run --extra dev pytest -q tests/api/test_pipeline_catalog.py`

  Expected: PASS。

  Commit: `feat-定义阶段输入与完成标准`

### Task 2: 有界 StageExecutionContext 加载器

**Files:**
- Create: `src/agent_forge/pipeline/execution_context.py`
- Create: `tests/pipeline/test_execution_context.py`

**Interfaces:**
- Consumes: `PipelineRun`、`PipelineStageState`、`StageDefinition`、`Artifact`。
- Produces: `build_stage_execution_context(...) -> StageExecutionContext` 和 `.to_context() -> dict`。

- [x] **Step 1: 写隔离、顺序、缺失和截断红灯测试**

  ```python
  context = await build_stage_execution_context(
      db_session,
      run=run,
      stage=design_stage,
      stage_definition=get_stage_definition("new_feature", "design"),
  )
  assert [item.artifact_id for item in context.upstream_artifacts] == [analysis_artifact.id]
  assert context.missing_input_artifact_types == ()
  assert foreign_artifact.id not in [
      item["artifact_id"] for item in context.to_context()["upstream_artifacts"]
  ]
  ```

- [x] **Step 2: 运行红灯测试**

  Run: `uv run --extra dev pytest -q tests/pipeline/test_execution_context.py`

  Expected: ERROR，模块尚不存在。

- [x] **Step 3: 实现 dataclass、查询、过滤和截断**

  ```python
  stage_by_state_id = {item.id: item for item in run.stages}
  candidates = [
      artifact
      for artifact in result.scalars().all()
      if artifact.stage_state_id in stage_by_state_id
      and stage_by_state_id[artifact.stage_state_id].order_index < stage.order_index
      and (
          not stage_definition.required_input_artifact_types
          or artifact.artifact_type in stage_definition.required_input_artifact_types
      )
  ]
  ```

  按 `(stage_order, created_at, artifact_id)` 排序后应用 6/4000/12000 预算；`.to_context()` 将 tuple 序列化为 list。

- [x] **Step 4: 运行加载器测试并提交**

  Run: `uv run --extra dev pytest -q tests/pipeline/test_execution_context.py`

  Expected: PASS。

  Commit: `feat-构建有界阶段执行上下文`

### Task 3: Runtime 与 Engine Prompt 分层

**Files:**
- Modify: `src/agent_forge/pipeline/runtime.py`
- Modify: `src/agent_forge/skills/engine.py`
- Modify: `tests/pipeline/test_runtime.py`
- Modify: `tests/skills/test_engine_context.py`

**Interfaces:**
- Consumes: `StageExecutionContext.to_context()`。
- Produces: `advanced_context["stage_execution"]`、trusted system metadata、untrusted user-level Artifact reference prompt。

- [x] **Step 1: 写 Runtime 和 Engine 红灯测试**

  ```python
  stage_context = fake_engine.kwargs["advanced_context"]["stage_execution"]
  assert stage_context["stage_id"] == "locate"
  assert stage_context["expected_output_artifact_types"] == ["report"]

  prompt = _build_system_prompt("CodeSoul", advanced_context)
  assert "定位问题现象" in prompt
  assert "ignore previous instructions" not in prompt
  assert 'trust_level="untrusted"' in _build_upstream_artifact_prompt(advanced_context)
  assert "&lt;/upstream_artifact&gt;" in _build_upstream_artifact_prompt(advanced_context)
  ```

- [x] **Step 2: 运行红灯测试**

  Run: `uv run --extra dev pytest -q tests/pipeline/test_runtime.py tests/skills/test_engine_context.py -k 'stage_execution or upstream_artifact'`

  Expected: FAIL，当前无 `stage_execution`。

- [x] **Step 3: 接入 Runtime 和三条 Engine 回复路径**

  ```python
  reference_prompt = _build_upstream_artifact_prompt(advanced_context)
  messages = [
      {"role": "system", "content": system_prompt},
      *([{"role": "user", "content": reference_prompt}] if reference_prompt else []),
      *conversation_history,
      {"role": "user", "content": user_message},
  ]
  ```

  无工具路径使用 `_build_direct_reply_prompt(user_message, reference_prompt)`；工具结果路径使用 `_build_final_prompt(messages, reference_prompt)`。Artifact 正文由 `html.escape(content)` 转义后放入 untrusted 标签。

- [x] **Step 4: 运行 Runtime、Engine 和安全回归并提交**

  Run: `uv run --extra dev pytest -q tests/pipeline/test_runtime.py tests/skills/test_engine_context.py tests/security/test_prompt_injection.py`

  Expected: PASS，允许既有 security skip/xfail/warning。

  Commit: `feat-将阶段执行上下文接入运行时`

### Task 4: Artifact 类型单一事实源

**Files:**
- Modify: `src/agent_forge/artifacts/service.py`
- Modify: `src/agent_forge/pipeline/runtime.py`
- Modify: `tests/pipeline/test_runtime.py`

**Interfaces:**
- Consumes: `StageDefinition.output_artifact_types[0]`。
- Produces: 与 Catalog 一致的 `Artifact.artifact_type`。

- [ ] **Step 1: 写非硬编码 Artifact 类型红灯测试**

  ```python
  original = get_stage_definition("bug_fix", "locate")
  monkeypatch.setattr(
      runtime_module,
      "get_stage_definition",
      lambda *_args: replace(original, output_artifact_types=("architecture",)),
  )
  assert artifact.artifact_type == "architecture"
  ```

  上述 monkeypatch 和断言加入现有 `test_stage_runtime_creates_artifact_for_completed_stage`，复用该测试已经完整构造的 Project、Session、PipelineRun 和 Runtime 执行过程。

- [ ] **Step 2: 运行红灯测试**

  Run: `uv run --extra dev pytest -q tests/pipeline/test_runtime.py -k catalog_artifact_type`

  Expected: FAIL，当前仍使用 `_STAGE_ARTIFACT_TYPE`。

- [ ] **Step 3: 删除阶段类型映射并接入 Catalog**

  ```python
  def infer_stage_artifact_type(stage_id: str, intent_type: str | None = None) -> str:
      if intent_type is not None:
          definition = get_stage_definition(intent_type, stage_id)
          if definition and definition.output_artifact_types:
              return definition.output_artifact_types[0]
      candidates = {
          stage.output_artifact_types[0]
          for pipeline in list_pipeline_definitions()
          for stage in pipeline.stages
          if stage.stage_id == stage_id and stage.output_artifact_types
      }
      return candidates.pop() if len(candidates) == 1 else "report"

  artifact_type = stage_definition.output_artifact_types[0]
  if artifact_type not in ARTIFACT_TYPES:
      raise ValueError(f"Unsupported artifact type: {artifact_type}")
  ```

  `StageRuntime._complete_stage()` 重新读取当前 Run 的 StageDefinition，并把第一输出类型显式传给 `create_stage_artifact()`。

- [ ] **Step 4: 运行 Artifact 与 Pipeline 回归并提交**

  Run: `uv run --extra dev pytest -q tests/pipeline/test_runtime.py tests/api/test_projects.py tests/api/test_pipeline_catalog.py`

  Expected: PASS。

  Commit: `refactor-收敛阶段产物类型事实源`

### Task 5: 文档、完整验证与集成

**Files:**
- Modify: `docs/iterations/2026-07-15-stage-execution-context/TASK-CHECKLIST.md`
- Create: `docs/iterations/2026-07-15-stage-execution-context/ITERATION-REVIEW.md`
- Modify: `docs/iterations/2026-07-15-core-workflow-execution-chain/TASK-CHECKLIST.md`
- Modify: `docs/architecture/AI-RUNTIME-CONVERGENCE.md`
- Modify: `docs/README.md`
- Modify: `MEMORY.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Produces: TASK-047 当前事实、验证证据和 TASK-048 输入边界。

- [ ] **Step 1: 同步架构与迭代事实**

  更新推荐架构入口、任务索引、路线图状态和迭代复盘，不把计划行为写成已实现。

- [ ] **Step 2: 执行相关和全量验证**

  Run: `uv run --extra dev pytest -q tests/api/test_pipeline_catalog.py tests/pipeline/test_execution_context.py tests/pipeline/test_runtime.py tests/skills/test_engine_context.py tests/security/test_prompt_injection.py`

  Run: `uv run --extra dev pytest -q`

  Expected: 新增测试与基线全部通过，允许既有 skip/xfail/warning。

- [ ] **Step 3: 验证 FastAPI 生命周期并恢复测试数据库**

  Run: `PYTHONPATH=src JWT_SECRET_KEY=test-secret .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 18147`

  Expected: 到达 `Application startup complete`；恢复 `test_db.sqlite`。

- [ ] **Step 4: 提交、推送、审查和合并**

  Commit: `feat-完成阶段执行上下文迭代`

  推送 `feature/task-047-stage-execution-context`，独立审查无阻断问题后 fast-forward 合并并推送 `main`。
