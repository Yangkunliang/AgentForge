# TASK-047 技术设计：StageExecutionContext

## 领域契约

`StageDefinition` 新增：

```python
required_input_artifact_types: tuple[str, ...] = ()
success_criteria: tuple[str, ...] = ()
```

### 阶段契约表

| Intent | Stage | 必需输入类型 | 完成标准 |
|---|---|---|---|
| new_feature | analysis | 无 | 明确用户目标与角色；列出范围、非目标和验收标准 |
| new_feature | design | prd | 定义模块边界和数据流；说明接口、技术取舍和风险 |
| new_feature | db_api | prd, architecture | 定义数据模型与迁移；定义 API 契约、错误和权限 |
| new_feature | task_split | prd, architecture, api_spec | 拆成可独立验证和提交的任务；声明依赖、文件范围和测试命令 |
| new_feature | ui_prototype | prd | 覆盖页面结构、关键状态和响应式；给出视觉验收点 |
| new_feature | backend_dev | prd, architecture, api_spec, report | 实现后端与自动化测试；说明改动文件和回归结果 |
| new_feature | frontend_dev | prd, api_spec, report | 实现前端交互与错误状态；构建通过并说明视觉验收 |
| new_feature | testing | prd, code | 执行目标与相关回归；记录命令、结果、失败和残余风险 |
| iteration | diff | 无 | 描述旧行为、新行为和不变范围；给出验收差异 |
| iteration | impact | diff | 列出受影响模块、文件和 API；定义回归范围和风险 |
| iteration | backend_dev | diff | 实现最小后端改动与测试；保持无关行为不变 |
| iteration | frontend_dev | diff | 实现必要前端改动与状态；构建结果可复核 |
| iteration | regression | diff, code | 执行变更点和相关回归；记录失败与残余风险 |
| ui_adjust | prototype_diff | 无 | 明确布局、视觉和交互差异；列出响应式和状态验收点 |
| ui_adjust | frontend_dev | diff | 实现组件、样式和交互；覆盖加载、空、错和禁用状态 |
| ui_adjust | visual | diff, code | 检查响应式、溢出和一致性；记录视觉验收结论 |
| bug_fix | locate | 无 | 给出可复现现象和根因证据；区分事实与假设 |
| bug_fix | impact_scope | report | 列出受影响路径和风险；定义最小修复与回归范围 |
| bug_fix | fix | report | 实现最小修复和回归测试；不扩大无关改动 |
| bug_fix | regression | report, code | 复现用例转绿；相关回归通过并记录残余风险 |

新增 `src/agent_forge/pipeline/execution_context.py`：

```python
@dataclass(frozen=True)
class UpstreamArtifactContext:
    artifact_id: str
    stage_id: str
    stage_name: str
    stage_order: int
    artifact_type: str
    name: str
    content: str
    content_truncated: bool

@dataclass(frozen=True)
class StageExecutionContext:
    project_id: str
    session_id: str
    pipeline_run_id: str
    intent_type: str
    stage_id: str
    stage_name: str
    stage_order: int
    description: str
    required_input_artifact_types: tuple[str, ...]
    expected_output_artifact_types: tuple[str, ...]
    success_criteria: tuple[str, ...]
    missing_input_artifact_types: tuple[str, ...]
    upstream_artifacts: tuple[UpstreamArtifactContext, ...]
```

## 加载规则

`build_stage_execution_context(db, run, stage, stage_definition)` 使用已完成用户校验的 PipelineRun，只查询 `project_id == run.project_id` 且 `pipeline_run_id == run.id` 的 Artifact。通过 `stage_state_id` 映射真实阶段顺序，仅保留 `order_index < current_stage.order_index` 的前序产物。

默认边界：

- `max_artifacts = 6`
- `max_artifact_content_chars = 4000`
- `max_total_content_chars = 12000`

必需类型存在时只选择相关类型；缺失类型写入上下文但暂不阻断，硬门禁留给 VerificationGate。

Artifact 查询边界由一个独立 helper 固定：

```python
async def _load_run_artifacts(db: AsyncSession, run: PipelineRun) -> list[Artifact]:
    result = await db.execute(
        select(Artifact)
        .where(
            Artifact.project_id == run.project_id,
            Artifact.pipeline_run_id == run.id,
        )
        .order_by(Artifact.created_at.asc(), Artifact.id.asc())
    )
    return list(result.scalars().all())
```

`build_stage_execution_context()` 只在该结果上使用 `stage_state_id` 对应的 `order_index` 做前序过滤、按类型筛选和长度预算，不增加额外查询来源。

## Prompt 分层

- system prompt：阶段 id、名称、目标、输入/输出类型、完成标准和缺失输入，仅包含 Catalog 可信元数据。
- user-level reference prompt：上游 Artifact 内容，使用 `<upstream_artifact trust_level="untrusted">` 包裹，并对 `& < >` 转义。
- tool-use、无工具直接回复、工具结果后最终回复三条路径都必须携带同一份上游参考内容。

## Artifact 类型收敛

删除 `_STAGE_ARTIFACT_TYPE` 语义映射。`infer_stage_artifact_type(stage_id, intent_type)` 和 StageRuntime 均从 Catalog 读取 `output_artifact_types[0]`；`create_stage_artifact()` 对传入类型做 allowlist 校验。当前每阶段只生成一个 Markdown Artifact，多产物拆分不在本任务范围。

## 兼容性与风险

- `advanced_context["stage_execution"]` 是新增兼容字段。
- 历史 Artifact 不变，不新增数据库字段。
- 内容截断按 Python 字符计数，不承诺精确 token 数。
- Prompt 不记录 API Key、Credential 或文件系统未授权内容。
