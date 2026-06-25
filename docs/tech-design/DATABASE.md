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

## 2. 关系图

```
User 1───n Task
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
