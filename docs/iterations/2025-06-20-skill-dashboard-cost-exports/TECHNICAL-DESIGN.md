# TASK-004 技术设计

## 1. Skill 管理 API

### 1.1 数据模型

```python
class SkillInstall(BaseModel):
    install_id: str
    skill_name: str
    source: str
    version: str
    status: str  # pending | installing | done | failed
    log: str
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

class SkillManifest(BaseModel):
    name: str
    version: str
    description: str
    entry_point: str
    installed_at: datetime
```

### 1.2 核心逻辑

使用 `subprocess` 异步执行 `pip install`，通过 `watchdog` 监控安装进度。

### 1.3 API 路由

- `POST /api/v1/skills/install` → `skill_router.py`
- `GET /api/v1/skills/install/{install_id}` → `skill_router.py`
- `GET /api/v1/skills` → `skill_router.py`
- `DELETE /api/v1/skills/{skill_name}` → `skill_router.py`

## 2. Dashboard API

### 2.1 数据模型

```python
class DashboardStats(BaseModel):
    tasks: TaskStats
    agents: AgentStats
    skills: SkillStats
    cost: CostStats
    recent_tasks: List[TaskSummary]
```

### 2.2 核心逻辑

聚合查询数据库：
- 任务状态分布（COUNT + GROUP BY status）
- Agent 状态分布（COUNT + GROUP BY status）
- 费用统计（SUM + GROUP BY date）

## 3. 费用统计 API

### 3.1 数据模型

```python
class DailyCost(BaseModel):
    date: str
    total_cost_usd: float
    model_costs: Dict[str, float]
    total_tasks: int
    avg_cost_per_task: float
```

## 4. 数据导出 API

### 4.1 数据模型

```python
class ExportTask(BaseModel):
    export_id: str
    type: str
    status: str  # processing | done | failed
    total_records: int
    estimated_size_mb: float
    file_path: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
```

### 4.2 脱敏策略

- Level 1：移除 email、phone、姓名
- Level 2：模糊处理 IP、地址
- Level 3：完全随机化敏感字段

### 4.3 导出格式

JSONL（每行一条完整记录）：
```json
{"user_input": "...", "agent_selection": "...", "skill_calls": [...], "result": "...", "feedback": "..."}
```

## 5. 文件结构

```
src/agent_forge/
├── api/routes/
│   ├── skills.py        # Skill API
│   ├── dashboard.py     # Dashboard API
│   ├── cost.py          # 费用统计 API
│   └── exports.py       # 数据导出 API
├── skills/
│   ├── manager.py       # Skill 管理器
│   ├── installer.py     # Skill 安装器
│   └── deserializer.py  # Skill 反序列化器
└── exporter/
    ├── manager.py       # 导出管理器
    └── anonymizer.py    # 数据脱敏器
```