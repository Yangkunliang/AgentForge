import request from '../request'
import type { Agent, AgentExpertise, CreateAgentForm } from '@/types'

export interface AgentListParams {
  status?: string
  capability?: string
}

export const agentsApi = {
  list: (params?: AgentListParams) => {
    return request.get<Agent[]>('/agents', { params })
  },

  get: (agentId: string) => {
    return request.get<Agent>(`/agents/${agentId}`)
  },

  create: (data: CreateAgentForm) => {
    return request.post<Agent>('/agents', data)
  },

  update: (agentId: string, data: Partial<CreateAgentForm>) => {
    return request.patch<Agent>(`/agents/${agentId}`, data)
  },

  delete: (agentId: string) => {
    return request.delete(`/agents/${agentId}`)
  },

  // 用户级 AI 助手设置
  getMySettings: () => {
    return request.get<{ agent_name: string; avatar_url: string | null }>('/agents/settings/me')
  },

  updateMySettings: (data: { name?: string; avatar_url?: string | null }) => {
    return request.patch<{ agent_name: string; avatar_url: string | null }>('/agents/settings/me', data)
  },

  // AI 辅助抽取：从工作素材蒸馏出专家模型草稿
  extractExpertise: (data: { source_text: string; role_hint?: string }) => {
    return request.post<AgentExpertise>('/agents/expertise/extract', data)
  },
}
