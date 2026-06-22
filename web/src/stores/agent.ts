import { defineStore } from 'pinia'
import { ref } from 'vue'
import { agentsApi, type AgentListParams } from '@/api/modules/agents'
import type { Agent, CreateAgentForm } from '@/types'

export const useAgentStore = defineStore('agent', () => {
  const agents = ref<Agent[]>([])
  const currentAgent = ref<Agent | null>(null)
  const loading = ref(false)

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

  return {
    agents,
    currentAgent,
    loading,
    fetchAgents,
    fetchAgent,
    createAgent,
    updateAgent,
    deleteAgent,
    clearCurrentAgent,
  }
})
