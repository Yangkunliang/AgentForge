import request from '../request'
import type { Agent, CreateAgentForm } from '@/types'

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
}
