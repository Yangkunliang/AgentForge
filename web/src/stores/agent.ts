import { defineStore } from 'pinia'
import { ref } from 'vue'
import { agentsApi, type AgentListParams } from '@/api/modules/agents'
import type { Agent, CreateAgentForm } from '@/types'

export const useAgentStore = defineStore('agent', () => {
  const agents = ref<Agent[]>([])
  const currentAgent = ref<Agent | null>(null)
  const loading = ref(false)

  const myAgentSettings = ref<{ agent_name: string; avatar_url: string | null }>({
    agent_name: 'CodeSoul',
    avatar_url: null,
  })

  async function fetchAgents(params?: AgentListParams) {
    loading.value = true
    try {
      const { data } = await agentsApi.list(params)
      agents.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchAgent(agentId: string) {
    loading.value = true
    try {
      const { data } = await agentsApi.get(agentId)
      currentAgent.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function createAgent(form: CreateAgentForm) {
    loading.value = true
    try {
      const { data } = await agentsApi.create(form)
      return data
    } finally {
      loading.value = false
    }
  }

  async function updateAgent(agentId: string, form: Partial<CreateAgentForm>) {
    loading.value = true
    try {
      const { data } = await agentsApi.update(agentId, form)
      return data
    } finally {
      loading.value = false
    }
  }

  async function deleteAgent(agentId: string) {
    loading.value = true
    try {
      await agentsApi.delete(agentId)
      agents.value = agents.value.filter((a) => a.id !== agentId)
    } finally {
      loading.value = false
    }
  }

  function clearCurrentAgent() {
    currentAgent.value = null
  }

  async function fetchMyAgentSettings() {
    try {
      const { data } = await agentsApi.getMySettings()
      myAgentSettings.value = {
        agent_name: data.agent_name,
        avatar_url: data.avatar_url || null,
      }
      return data
    } catch {
      // ignore
    }
  }

  function updateMyAgentSettings(settings: { agent_name: string; avatar_url: string | null }) {
    myAgentSettings.value = settings
  }

  return {
    agents,
    currentAgent,
    loading,
    myAgentSettings,
    fetchAgents,
    fetchAgent,
    createAgent,
    updateAgent,
    deleteAgent,
    clearCurrentAgent,
    fetchMyAgentSettings,
    updateMyAgentSettings,
  }
})
