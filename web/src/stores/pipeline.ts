import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pipelineRunsApi } from '@/api/modules/pipelineRuns'
import type { ChatIntentType, PipelineRun, StageConfirmationAction } from '@/types'

export const usePipelineStore = defineStore('pipeline', () => {
  const currentRun = ref<PipelineRun | null>(null)
  const loading = ref(false)
  const mutatingStageId = ref<string | null>(null)

  function setCurrentRun(run: PipelineRun | null) {
    currentRun.value = run
  }

  function clearRun() {
    currentRun.value = null
    mutatingStageId.value = null
  }

  async function fetchRun(runId: string | null | undefined) {
    if (!runId) {
      clearRun()
      return null
    }

    loading.value = true
    try {
      const { data } = await pipelineRunsApi.get(runId)
      currentRun.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function createForSession(
    sessionId: string,
    intentType?: ChatIntentType | null,
    stageOverrides?: Record<string, boolean>,
  ) {
    const { data } = await pipelineRunsApi.createForSession(sessionId, {
      intent_type: intentType ?? null,
      stage_overrides: stageOverrides ?? {},
    })
    currentRun.value = data
    return data
  }

  async function skipStage(stageId: string) {
    if (!currentRun.value) return null
    mutatingStageId.value = stageId
    try {
      const { data } = await pipelineRunsApi.skipStage(currentRun.value.id, stageId)
      currentRun.value = data
      return data
    } finally {
      mutatingStageId.value = null
    }
  }

  async function restoreStage(stageId: string) {
    if (!currentRun.value) return null
    mutatingStageId.value = stageId
    try {
      const { data } = await pipelineRunsApi.restoreStage(currentRun.value.id, stageId)
      currentRun.value = data
      return data
    } finally {
      mutatingStageId.value = null
    }
  }

  async function startStage(stageId: string) {
    if (!currentRun.value) return null
    const { data } = await pipelineRunsApi.startStage(currentRun.value.id, stageId)
    currentRun.value = data
    return data
  }

  async function completeStage(stageId: string) {
    if (!currentRun.value) return null
    const { data } = await pipelineRunsApi.completeStage(currentRun.value.id, stageId)
    currentRun.value = data
    return data
  }

  async function confirmStage(
    stageId: string,
    action: StageConfirmationAction,
    feedback?: string | null,
  ) {
    if (!currentRun.value) return null
    mutatingStageId.value = stageId
    try {
      const { data } = await pipelineRunsApi.confirmStage(currentRun.value.id, stageId, {
        action,
        feedback: feedback ?? null,
      })
      currentRun.value = data
      return data
    } finally {
      mutatingStageId.value = null
    }
  }

  async function failStage(stageId: string) {
    if (!currentRun.value) return null
    const { data } = await pipelineRunsApi.failStage(currentRun.value.id, stageId)
    currentRun.value = data
    return data
  }

  return {
    currentRun,
    loading,
    mutatingStageId,
    setCurrentRun,
    clearRun,
    fetchRun,
    createForSession,
    skipStage,
    restoreStage,
    startStage,
    completeStage,
    confirmStage,
    failStage,
  }
})
