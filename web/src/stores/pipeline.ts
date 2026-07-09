import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { pipelineCatalogApi } from '@/api/modules/pipelineCatalog'
import { pipelineRunsApi } from '@/api/modules/pipelineRuns'
import type { ChatIntentType, PipelineIntentCatalog, PipelineRun, StageConfirmationAction } from '@/types'

export const usePipelineStore = defineStore('pipeline', () => {
  const currentRun = ref<PipelineRun | null>(null)
  const catalog = ref<Record<ChatIntentType, PipelineIntentCatalog | undefined>>({
    new_feature: undefined,
    iteration: undefined,
    ui_adjust: undefined,
    bug_fix: undefined,
  })
  const loading = ref(false)
  const catalogLoading = ref(false)
  const catalogLoaded = ref(false)
  const mutatingStageId = ref<string | null>(null)

  const catalogItems = computed(() =>
    Object.values(catalog.value).filter((item): item is PipelineIntentCatalog => Boolean(item)),
  )

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

  async function fetchCatalog(force = false) {
    if (catalogLoaded.value && !force) return catalogItems.value
    catalogLoading.value = true
    try {
      const { data } = await pipelineCatalogApi.list()
      catalog.value = {
        new_feature: undefined,
        iteration: undefined,
        ui_adjust: undefined,
        bug_fix: undefined,
      }
      for (const item of data.items) {
        catalog.value[item.intent_type] = item
      }
      catalogLoaded.value = true
      return catalogItems.value
    } finally {
      catalogLoading.value = false
    }
  }

  function catalogForIntent(intentType: ChatIntentType): PipelineIntentCatalog | null {
    return catalog.value[intentType] ?? null
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
    catalog,
    catalogItems,
    loading,
    catalogLoading,
    catalogLoaded,
    mutatingStageId,
    setCurrentRun,
    clearRun,
    fetchCatalog,
    catalogForIntent,
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
