# 多智能体协同框架 - 数据库设计 (DATABASE.md)

## 1. 核心实体

### 1.1 用户 (User)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | String | 用户名（唯一） |
| email | String | 邮箱（唯一） |
| password_hash | String | 密码哈希 (bcrypt) |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 1.2 任务 (Task)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → User(id) ON DELETE CASCADE |
| description | Text | 任务描述 |
| status | Enum | pending/processing/completed/failed |
| result | Text | 任务结果 |
| priority | Enum | low/medium/high |
| trace_id | String | 全链路追踪 ID |
| created_at | DateTime | 创建时间 |
| completed_at | DateTime | 完成时间 |

### 1.3 子任务 (SubTask)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| task_id | UUID | 外键 → Task(id) ON DELETE CASCADE |
| description | Text | 子任务描述 |
| status | Enum | pending/processing/completed/failed |
| assigned_agent_id | UUID | 外键 → Agent(id) ON DELETE SET NULL |
| result | Text | 子任务结果 |

### 1.4 Agent
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | String | Agent 名称 |
| capabilities | JSON | 能力列表，如 `["code_review", "code_gen"]` |
| model | String | 使用的 LLM 模型 |
| status | Enum | active/inactive |
| created_at | DateTime | 创建时间 |

### 1.5 Skill
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | String | Skill 名称（唯一） |
| version | String | 版本号 (Semantic Versioning) |
| description | Text | Skill 描述 |
| entry_point | String | 入口路径，如 `skill.main` |
| manifest | JSON | Skill 声明（inputs/outputs schema） |
| dependencies | JSON | 依赖列表，如 `["ruff", "mypy"]` |
| installed_at | DateTime | 安装时间 |

### 1.6 Agent-Skill 关联 (AgentSkill)
| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | UUID | 外键 → Agent(id) ON DELETE CASCADE |
| skill_id | UUID | 外键 → Skill(id) ON DELETE CASCADE |
| 主键 | (agent_id, skill_id) | 复合主键 |

### 1.7 任务执行记录 (TaskExecution) — 用于数据导出
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| task_id | UUID | 外键 → Task(id) ON DELETE CASCADE |
| sub_task_id | UUID | 外键 → SubTask(id) ON DELETE SET NULL |
| agent_id | UUID | 外键 → Agent(id) ON DELETE SET NULL |
| skill_id | UUID | 外键 → Skill(id) ON DELETE SET NULL |
| input | JSON | 输入参数 |
| output | JSON | 输出结果 |
| tokens_used | JSON | token 消耗 `{"prompt": 1200, "completion": 800}` |
| cost_usd | Float | 成本（美元） |
| duration_ms | Int | 耗时（毫秒） |
| model_used | String | 使用的模型 |
| status | Enum | success/failed |
| user_feedback | JSON | 用户反馈 `{"thumbs": 1, "rating": 4}` |
| created_at | DateTime | 创建时间 |

### 1.8 对话记录 (Conversation) — 用于记忆状态
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| task_id | UUID | 外键 → Task(id) ON DELETE CASCADE |
| from_agent | UUID | 发送方 Agent |
| to_agent | UUID | 接收方 Agent（NULL = 广播） |
| message_type | Enum | bid/message/result |
| content | JSON | 消息内容 |
| created_at | DateTime | 创建时间 |

### 1.9 API Key
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → User(id) ON DELETE CASCADE |
| key_hash | String | API Key 哈希 (SHA256) |
| name | String | 名称 |
| permissions | JSON | 权限列表 `["read", "write"]` |
| active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |

### 1.10 项目 (Project)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → User(id) ON DELETE CASCADE |
| name | String | 用户自定义项目展示名称 |
| description | Text | 项目说明 |
| tech_tags | JSON | 技术栈标签，如 `["FastAPI", "Vue 3"]` |
| status | String | active/archived |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 1.11 项目挂载 (ProjectMount)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID | 外键 → Project(id) ON DELETE CASCADE |
| mount_type | String | local/github/upload |
| display_name | String | 挂载入口展示名称 |
| locator | Text | 本地路径、GitHub URL 或 upload 标识 |
| role | String | primary/reference/docs |
| status | String | connected/disconnected/pending/error |
| metadata | JSON | 附加信息，预留 Bridge、GitHub、上传文件元数据 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 1.12 会话扩展 (Session)
`sessions` 表已从纯聊天会话扩展为项目内开发任务上下文。

| 字段 | 类型 | 说明 |
|------|------|------|
| project_id | UUID | 外键 → Project(id) ON DELETE SET NULL；新会话应归属项目 |
| intent_type | String | new_feature/iteration/ui_adjust/bug_fix |
| current_pipeline_run_id | UUID | 当前运行中的 PipelineRun |

历史无 `project_id` 的会话由 `0010` 迁移为每个用户创建“默认项目”并回填。

### 1.13 PipelineRun
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID | 外键 → Project(id) ON DELETE CASCADE |
| session_id | UUID | 外键 → Session(id) ON DELETE CASCADE |
| intent_type | String | new_feature/iteration/ui_adjust/bug_fix |
| status | String | planned/running/completed/failed |
| current_stage_id | String | 当前待执行或运行中的 stage_id |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 1.14 PipelineStageState
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| pipeline_run_id | UUID | 外键 → PipelineRun(id) ON DELETE CASCADE |
| stage_id | String | 稳定阶段标识，如 `diff`、`backend_dev` |
| stage_name | String | 展示名称，如“需求 Diff” |
| order_index | Int | 阶段顺序 |
| required | Boolean | 是否必需阶段；仅可选阶段支持 skip/restore |
| status | String | pending/running/waiting_confirmation/completed/skipped/failed |
| skip_reason | String | user_override/user_skipped 等跳过原因 |
| confirmation_required | Boolean | 是否需要人工确认，TASK-017 完整接入 |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成或跳过时间 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 1.15 产物 (Artifact)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID | 外键 → Project(id) ON DELETE CASCADE |
| session_id | UUID | 外键 → Session(id) ON DELETE SET NULL |
| pipeline_run_id | UUID | 关联 PipelineRun(id)，TASK-016 后由 StageRuntime 写入 |
| stage_state_id | UUID | 关联 PipelineStageState(id)，TASK-016 后由 StageRuntime 写入 |
| artifact_type | String | prd/architecture/api_spec/code/test/report/diff |
| name | String | 产物名称 |
| content | Text | MVP 阶段直接存储正文内容 |
| file_type | String | markdown/json/text/diff 等 |
| source_message_id | UUID | 外键 → chat_messages(id) ON DELETE SET NULL |
| metadata | JSON | 阶段、来源、上下文等附加信息 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

TASK-016 后，StageRuntime 会在阶段完成时根据 `stage_id` 映射 `artifact_type` 并写入 Artifact；`source_message_id` 指向本次 assistant 消息，供 Chat 消息列表回带 ArtifactCard。

## 2. 关系图

```
User 1───n Task
User 1───n Project
Project 1───n ProjectMount
Project 1───n Session
Project 1───n PipelineRun
Project 1───n Artifact
Session 1───n PipelineRun
Session 1───n Artifact
PipelineRun 1───n PipelineStageState
Task 1───n SubTask
Task 1───n TaskExecution
Task 1───n Conversation

Agent 1───n SubTask (assigned)
Agent 1───n TaskExecution
Agent 1───n Conversation (from)
Agent 1───n Conversation (to)
Agent 1───n AgentSkill
AgentSkill 1──n Skill

Skill 1───n TaskExecution
Skill 1───n AgentSkill
```

## 3. 索引设计

```sql
-- 任务查询
CREATE INDEX idx_task_user_id ON Task(user_id);
CREATE INDEX idx_task_status ON Task(status);
CREATE INDEX idx_task_trace_id ON Task(trace_id);

-- 子任务查询
CREATE INDEX idx_subtask_task_id ON SubTask(task_id);

-- 执行记录查询（数据导出）
CREATE INDEX idx_execution_task_id ON TaskExecution(task_id);
CREATE INDEX idx_execution_agent_id ON TaskExecution(agent_id);
CREATE INDEX idx_execution_created_at ON TaskExecution(created_at);

-- 对话记录查询
CREATE INDEX idx_conversation_task_id ON Conversation(task_id);
CREATE INDEX idx_conversation_from ON Conversation(from_agent);

-- API Key
CREATE INDEX idx_apikey_user_id ON APIKey(user_id);

-- 核心开发闭环
CREATE INDEX ix_projects_user_id ON projects(user_id);
CREATE INDEX ix_projects_status ON projects(status);
CREATE INDEX ix_project_mounts_project_id ON project_mounts(project_id);
CREATE INDEX ix_sessions_project_id ON sessions(project_id);
CREATE INDEX ix_artifacts_project_id ON artifacts(project_id);
CREATE INDEX ix_artifacts_session_id ON artifacts(session_id);
CREATE INDEX ix_artifacts_pipeline_run_id ON artifacts(pipeline_run_id);
CREATE INDEX ix_pipeline_runs_project_id ON pipeline_runs(project_id);
CREATE INDEX ix_pipeline_runs_session_id ON pipeline_runs(session_id);
CREATE INDEX ix_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX ix_pipeline_stage_states_pipeline_run_id ON pipeline_stage_states(pipeline_run_id);
CREATE INDEX ix_pipeline_stage_states_stage_id ON pipeline_stage_states(stage_id);
CREATE INDEX ix_pipeline_stage_states_status ON pipeline_stage_states(status);
```

## 5. 记忆系统表

### 5.1 语义记忆 (SemanticEntry)

跨会话语义记忆，支持向量相似度检索。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → User(id) ON DELETE CASCADE |
| task_id | UUID | 外键 → Task(id) ON DELETE SET NULL |
| title | String | 标题（最多 500 字符） |
| content | Text | 记忆内容 |
| category | String | 类别（decision/code/design/result/context/preference） |
| metadata | JSONB | 附加元数据 |
| embedding | vector(1536) | 向量嵌入（pgvector） |
| version | Int | 版本号（更新时递增） |
| deleted | Boolean | 软删除标记 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

```sql
-- 向量索引（HNSW 加速相似度搜索）
CREATE INDEX ON semantic_entries USING hnsw (embedding vector_cosine_ops)
    WHERE deleted = FALSE;

-- 全文索引
CREATE INDEX ON semantic_entries USING gin(to_tsvector('english', content || ' ' || title));

-- 复合索引
CREATE INDEX ix_semantic_user_category ON semantic_entries(user_id, category)
    WHERE deleted = FALSE;
```

### 5.2 用户记忆 (UserMemory)

用户级偏好与项目上下文，category 唯一约束。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → User(id) ON DELETE CASCADE |
| category | String | 类别（project_context/preference/style_guide/tech_stack） |
| content | Text | 记忆内容 |
| metadata | JSONB | 附加元数据 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 5.3 对话记忆 (ChatMessages)

用户对话历史（Episodic Memory），复用 `chat_messages` 表。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 主键 |
| session_id | String | 外键 → Session(id) ON DELETE CASCADE |
| role | String | 角色（user/assistant） |
| content | Text | 消息内容（全文搜索索引） |
| task_id | String | 外键 → Task(id) ON DELETE SET NULL |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

```sql
-- 全文搜索索引
CREATE INDEX ix_chat_messages_content_fts
    ON chat_messages USING gin(to_tsvector('english', content));
```

## 6. 数据库选型

| 项目 | 选型 | 说明 |
|------|------|------|
| 数据库 | PostgreSQL | 开发/生产统一使用 |
| ORM | SQLAlchemy 2.0 + asyncpg | 异步支持，类型安全 |
| 迁移 | Alembic | 版本化管理 |

### 4.1 Docker Compose 本地启动

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: agentforge
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: agent
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```
