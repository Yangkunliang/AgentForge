// 用户相关
export interface User {
  id: string
  username: string
  email: string
  permissions: string[]
  created_at: string
}

export interface LoginForm {
  username: string
  password: string
}

export interface RegisterForm {
  username: string
  email: string
  password: string
}

export interface AuthResponse {
  access_token: string
  expires_in: number
  user: User
}

// 任务相关
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
export type TaskPriority = 'low' | 'medium' | 'high'

export interface Task {
  task_id: string
  description: string
  status: TaskStatus
  priority: TaskPriority
  result?: string
  total_cost_usd?: number
  created_at: string
  completed_at?: string
  trace_id: string
}

export interface SubTask {
  id: string
  description: string
  status: TaskStatus
  assigned_agent_id?: string
  result?: string
}

export interface CreateTaskForm {
  description: string
  priority: TaskPriority
  expected_models?: string[]
}

export interface TaskFeedback {
  thumbs: 1 | -1
  rating?: number
  comment?: string
}

// Agent 相关
export interface Agent {
  agent_id: string
  name: string
  capabilities: string[]
  model: string
  status: 'active' | 'inactive'
  description?: string
  created_at: string
}

export interface CreateAgentForm {
  name: string
  capabilities: string[]
  model: string
  description?: string
}

// Skill 相关
export interface Skill {
  name: string
  version: string
  description: string
  entry_point: string | null
  installed_at?: string
  enabled: boolean
  source_type: string
  icon_url?: string
  tags: string[]
  github_url?: string
}

export interface MarketplaceSkill {
  name: string
  description: string
  url: string
  author: string
  icon?: string
  tags: string[]
  version: string
  stars: number
  source: 'github' | 'clawhub' | 'local'
}

export interface MarketplaceResponse {
  marketplace: string
  total: number
  items: MarketplaceSkill[]
}

export interface SkillInstall {
  install_id: string
  skill_name: string
  status: 'pending' | 'installing' | 'done' | 'failed'
  log?: string
  error?: string
}

export interface InstallSkillForm {
  source: string
  version?: string
}

// Dashboard 相关
export interface DashboardStats {
  tasks: {
    total: number
    pending: number
    processing: number
    completed: number
    failed: number
  }
  agents: {
    active: number
    inactive: number
  }
  skills: {
    total: number
  }
  cost: {
    today_usd: number
    trend_pct: number
    daily_7d: Array<{ date: string; usd: number }>
  }
  recent_tasks: Array<{
    task_id: string
    description: string
    status: TaskStatus
    total_cost_usd?: number
    created_at: string
  }>
}

// 导出相关
export interface ExportTask {
  export_id: string
  status: 'processing' | 'done' | 'failed'
  total_records: number
  estimated_size_mb: number
  file_path?: string
}

export interface CreateExportForm {
  type: string
  start_date?: string
  end_date?: string
  format?: string
  delevel?: string
}

// Webhook 相关
export interface Webhook {
  webhook_id: string
  url: string
  events: string[]
  is_active: boolean
  description?: string
}

// 工具调用
export interface WebSearchResult {
  title: string
  snippet: string
  url: string
}

export interface WebSearchResponse {
  query: string
  results: WebSearchResult[]
  total: number
}

// SSE 事件
export type SSEEventType =
  | 'task_started'
  | 'sub_task_created'
  | 'bid_received'
  | 'agent_selected'
  | 'message'
  | 'llm_response'
  | 'skill_called'
  | 'skill_result'
  | 'sub_task_completed'
  | 'task_completed'
  | 'task_failed'
  | 'heartbeat'

export interface SSEEvent {
  event: SSEEventType
  data: Record<string, unknown>
}

// 会话相关
export interface Session {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  task_id?: string
  created_at: string
  // 前端临时状态
  streaming?: boolean
  // 图片附件（用户上传或 AI 输出）
  images?: ChatImage[]
}

export interface ChatImage {
  url: string
  alt?: string
  /** 'upload' = 用户上传；'generated' = AI 生成 */
  type: 'upload' | 'generated'
}

// 通用响应
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  total: number
  page: number
  per_page: number
  items: T[]
}
