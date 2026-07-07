import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { usePipeline, type IntentType } from '@/composables/usePipeline'
import type { ChatAdvancedPayload, ContextFile } from '@/types'

const STORAGE_KEY = 'agentforge:advanced-settings'

interface PersistedAdvancedSettings {
  intent?: IntentType
  contextFiles?: ContextFile[]
  stageOverrides?: Record<string, boolean>
}

function createId(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `ctx-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function readPersistedSettings(): PersistedAdvancedSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as PersistedAdvancedSettings
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

export const useAdvancedSettingsStore = defineStore('advancedSettings', () => {
  const persisted = readPersistedSettings()
  const intent = ref<IntentType>(persisted.intent ?? 'iteration')
  const contextFiles = ref<ContextFile[]>(persisted.contextFiles ?? [])
  const stageOverrides = ref<Record<string, boolean>>(persisted.stageOverrides ?? {})
  const { getConfig } = usePipeline()

  const activeContextFiles = computed(() => contextFiles.value.filter((file) => file.active))

  const activeStages = computed(() => {
    return getConfig(intent.value).stages.filter((stage) => stageOverrides.value[stage.id] ?? true)
  })

  const chatPayload = computed<ChatAdvancedPayload>(() => {
    const payload: ChatAdvancedPayload = { intent: intent.value }

    if (activeContextFiles.value.length > 0) {
      payload.context_files = activeContextFiles.value.map((file) => ({
        type: file.type,
        value: file.value,
        label: file.label,
      }))
    }

    if (Object.keys(stageOverrides.value).length > 0) {
      payload.stage_overrides = { ...stageOverrides.value }
    }

    return payload
  })

  function setIntent(nextIntent: IntentType) {
    if (intent.value === nextIntent) return
    intent.value = nextIntent
    stageOverrides.value = {}
  }

  function addContextFile(file: Omit<ContextFile, 'id'>) {
    const value = file.value.trim()
    if (!value) return
    const exists = contextFiles.value.some(
      (item) => item.type === file.type && item.value === value,
    )
    if (exists) return
    contextFiles.value.push({
      ...file,
      id: createId(),
      value,
      label: file.label.trim() || value,
    })
  }

  function toggleContextFile(id: string) {
    const file = contextFiles.value.find((item) => item.id === id)
    if (file) file.active = !file.active
  }

  function removeContextFile(id: string) {
    contextFiles.value = contextFiles.value.filter((item) => item.id !== id)
  }

  function isStageEnabled(stageId: string): boolean {
    return stageOverrides.value[stageId] ?? true
  }

  function toggleStage(stageId: string) {
    if (stageOverrides.value[stageId] === false) {
      const next = { ...stageOverrides.value }
      delete next[stageId]
      stageOverrides.value = next
      return
    }
    stageOverrides.value[stageId] = false
  }

  function buildChatPayload(): ChatAdvancedPayload {
    return chatPayload.value
  }

  watch(intent, (_next, previous) => {
    if (previous !== undefined) stageOverrides.value = {}
  })

  watch(
    [intent, contextFiles, stageOverrides],
    () => {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          intent: intent.value,
          contextFiles: contextFiles.value,
          stageOverrides: stageOverrides.value,
        }),
      )
    },
    { deep: true },
  )

  return {
    intent,
    contextFiles,
    stageOverrides,
    activeContextFiles,
    activeStages,
    chatPayload,
    setIntent,
    addContextFile,
    toggleContextFile,
    removeContextFile,
    isStageEnabled,
    toggleStage,
    buildChatPayload,
  }
})
