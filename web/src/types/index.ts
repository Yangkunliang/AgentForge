// 用户相关
export interface User {
  id: string
  username: string
  email: string
  nickname?: string       // 可选昵称，未设置时显示 username
  avatar_url?: string    // base64 data URL 头像
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
  id: string
  name: string
  capabilities: string[]
  model: string
  status: 'active' | 'inactive'
  description?: string
  avatar_url?: string
  created_at: string
  updated_at: string
}

export interface CreateAgentForm {
  name: string
  capabilities: string[]
  model: string
  description?: string
  avatar_url?: string
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

// ── Execution Steps（TASK-009 SSE 执行过程可视化）─────────────

export type ExecutionStep = ThinkingStep | ToolCallStep | CodeExecutionStep

export interface ThinkingStep {
  type: 'thinking'
  content: string
  streaming: boolean
  duration_ms?: number
}

export interface ToolCallStep {
  type: 'tool_call'
  tool_name: string
  arguments: Record<string, unknown>
  status: 'running' | 'completed' | 'failed' | 'timeout'
  result?: Record<string, unknown>
  duration_ms?: number
}

export interface CodeExecutionStep {
  type: 'code_execution'
  code: string
  status: 'running' | 'completed' | 'failed' | 'timeout'
  stdout: string
  stderr: string
  exit_code?: number
  duration_ms?: number
}

export interface ToolCall {
  tool_name: string
  arguments: Record<string, unknown>
  status: 'running' | 'completed' | 'failed'
  result?: Record<string, unknown>
}

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

// 高级设置（TASK-011）
export type ChatIntentType = 'new_feature' | 'iteration' | 'ui_adjust' | 'bug_fix'
export type ContextFileType = 'branch' | 'file' | 'url' | 'artifact'

export interface ContextFile {
  id: string
  type: ContextFileType
  label: string
  value: string
  active: boolean
  mount_id?: string
}

export interface ChatAdvancedPayload {
  intent?: ChatIntentType
  context_files?: Array<{
      type: ContextFileType
      value: string
      label?: string
      mount_id?: string
  }>
  stage_overrides?: Record<string, boolean>
}

// Pipeline 运行态（TASK-015）
export type PipelineStageStatus =
  | 'pending'
  | 'running'
  | 'waiting_confirmation'
  | 'completed'
  | 'skipped'
  | 'failed'

export interface PipelineStageState {
  id: string
  pipeline_run_id: string
  stage_id: string
  stage_name: string
  order_index: number
  required: boolean
  status: PipelineStageStatus
  skip_reason?: string | null
  confirmation_required: boolean
  confirmation_action?: StageConfirmationAction | null
  confirmation_feedback?: string | null
  confirmation_resolved_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at: string
  updated_at: string
}

export type StageConfirmationAction = 'approve' | 'revise' | 'cancel'

export interface PipelineRun {
  id: string
  project_id: string
  session_id: string
  intent_type: ChatIntentType
  status: 'planned' | 'running' | 'waiting_confirmation' | 'completed' | 'failed' | 'cancelled' | string
  current_stage_id?: string | null
  created_at: string
  updated_at: string
  stages: PipelineStageState[]
}

export interface ChatResponse {
  message_id: string
  task_id: string
  pipeline_run_id?: string | null
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
  | 'tool_call_start'
  | 'tool_call_end'
  | 'sub_task_completed'
  | 'task_completed'
  | 'task_failed'
  | 'thinking_start'
  | 'thinking_delta'
  | 'thinking_end'
  | 'sandbox_executing'
  | 'sandbox_completed'
  | 'sandbox_timeout'
  | 'pipeline_started'
  | 'stage_started'
  | 'stage_completed'
  | 'stage_skipped'
  | 'artifact_created'
  | 'confirm_required'
  | 'confirm_resolved'
  | 'session_title_updated'
  | 'heartbeat'

export interface SSEEvent {
  event: SSEEventType
  data: Record<string, unknown>
}

// 会话相关
export interface Session {
  id: string
  project_id?: string | null
  title: string
  intent_type?: string | null
  current_pipeline_run_id?: string | null
  created_at: string
  updated_at: string
}

// 项目相关
export type ProjectStatus = 'active' | 'archived'
export type ProjectMountType = 'local' | 'github' | 'upload'
export type ProjectMountRole = 'primary' | 'reference' | 'docs'
export type ProjectMountStatus = 'connected' | 'disconnected' | 'pending' | 'error'

export interface Project {
  id: string
  user_id: string
  name: string
  display_name: string
  description?: string | null
  tech_tags: string[]
  status: ProjectStatus | string
  created_at: string
  updated_at: string
}

export interface CreateProjectForm {
  name: string
  description?: string | null
  tech_tags: string[]
}

export interface ProjectMount {
  id: string
  project_id: string
  mount_type: ProjectMountType | string
  display_name: string
  locator: string
  role: ProjectMountRole | string
  status: ProjectMountStatus | string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface BridgeStatusMount {
  mount_id: string
  mount_type: string
  display_name: string
  role: string
  status: ProjectMountStatus | string
  root_path?: string | null
}

export interface BridgeStatus {
  project_id: string
  connected_mounts: number
  mounts: BridgeStatusMount[]
}

export interface MountFileEntry {
  name: string
  relative_path: string
  kind: 'file' | 'directory'
  size?: number | null
  modified_at: string
}

export interface MountFileListResponse {
  mount_id: string
  project_id: string
  path: string
  entries: MountFileEntry[]
}

export interface MountFileReadResponse {
  mount_id: string
  project_id: string
  path: string
  content: string
  size: number
  truncated: boolean
}

export interface CreateProjectMountForm {
  mount_type: ProjectMountType
  display_name: string
  locator: string
  role: ProjectMountRole
  status: ProjectMountStatus
  metadata?: Record<string, unknown>
}

export type ArtifactType =
  | 'prd'
  | 'architecture'
  | 'api_spec'
  | 'code'
  | 'test'
  | 'report'
  | 'diff'

export interface Artifact {
  id: string
  project_id: string
  session_id?: string | null
  pipeline_run_id?: string | null
  stage_state_id?: string | null
  artifact_type: ArtifactType | string
  name: string
  content: string
  file_type?: 'markdown' | 'code' | 'text' | string | null
  source_message_id?: string | null
  metadata: Record<string, unknown>
  delivery_status: 'pending' | 'previewed' | 'delivered' | 'failed' | string
  delivery_target_path?: string | null
  delivered_at?: string | null
  delivery_report?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface CreateArtifactForm {
  session_id?: string | null
  pipeline_run_id?: string | null
  stage_state_id?: string | null
  artifact_type: ArtifactType
  name: string
  content: string
  file_type?: string | null
  source_message_id?: string | null
  metadata?: Record<string, unknown>
}

export interface DeliveryTargetPayload {
  mount_id: string
  target_path: string
}

export interface DeliveryApplyPayload extends DeliveryTargetPayload {
  confirm_write: boolean
  expected_target_hash?: string | null
}

export interface DeliveryResponse {
  artifact_id: string
  project_id: string
  mount_id: string
  target_path: string
  status: 'previewed' | 'delivered' | 'failed' | string
  has_changes: boolean
  unified_diff: string
  report: Record<string, unknown>
}

// ToolCall 已迁移为 ExecutionStep，此旧接口仅兼容历史消息
export interface LegacyToolCall {
  tool_name: string
  arguments: Record<string, unknown>
  status: 'running' | 'completed' | 'failed'
  result?: Record<string, unknown>
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
  // 新格式：执行步骤（TASK-009）
  execution_steps?: ExecutionStep[]
  // 旧格式：工具调用记录（deprecated，仅兼容历史消息）
  tool_calls?: LegacyToolCall[]
  // 阶段输出产物
  artifacts?: Artifact[]
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
