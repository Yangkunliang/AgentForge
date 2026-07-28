import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { usePipeline, type IntentType } from '@/composables/usePipeline'
import type {
  ChatAdvancedPayload,
  ContextFile,
  LinkedSkill,
  PipelineQuickAction,
} from '@/types'

const STORAGE_KEY = 'agentforge:advanced-settings'

interface PersistedAdvancedSettings {
  intent?: IntentType | null
  contextFiles?: ContextFile[]
  stageOverrides?: Record<string, boolean>
  skills?: Array<string | LinkedSkill>
  emphasis?: string[]
  appliedPresetId?: string | null
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

/** 兼容旧版 string[] 技能持久化 */
function normalizeSkills(raw: PersistedAdvancedSettings['skills']): LinkedSkill[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map((item): LinkedSkill | null => {
      if (typeof item === 'string') return { name: item, source: 'manual' }
      if (item && typeof item.name === 'string') {
        return { name: item.name, source: item.source === 'quick_action' ? 'quick_action' : 'manual' }
      }
      return null
    })
    .filter((s): s is LinkedSkill => s !== null)
}

export const useAdvancedSettingsStore = defineStore('advancedSettings', () => {
  const persisted = readPersistedSettings()
  const intent = ref<IntentType | null>(persisted.intent ?? null)
  const contextFiles = ref<ContextFile[]>(persisted.contextFiles ?? [])
  const stageOverrides = ref<Record<string, boolean>>(persisted.stageOverrides ?? {})
  const skills = ref<LinkedSkill[]>(normalizeSkills(persisted.skills))
  const emphasis = ref<string[]>(persisted.emphasis ?? [])
  const appliedPresetId = ref<string | null>(persisted.appliedPresetId ?? null)
  const { getConfig } = usePipeline()

  const activeContextFiles = computed(() => contextFiles.value.filter((file) => file.active))

  const activeStages = computed(() => {
    return getConfig(intent.value).stages.filter((stage) => stageOverrides.value[stage.id] ?? true)
  })

  const chatPayload = computed<ChatAdvancedPayload>(() => {
    const payload: ChatAdvancedPayload = {}

    if (intent.value) {
      payload.intent = intent.value
    }

    if (activeContextFiles.value.length > 0) {
      payload.context_files = activeContextFiles.value.map((file) => ({
        type: file.type,
        value: file.value,
        label: file.label,
        mount_id: file.mount_id,
      }))
    }

    if (Object.keys(stageOverrides.value).length > 0) {
      payload.stage_overrides = { ...stageOverrides.value }
    }

    if (skills.value.length > 0) {
      const allQuickAction = skills.value.every((s) => s.source === 'quick_action')
      payload.skill_authorization = {
        authorized_skill_names: skills.value.map((s) => s.name),
        authorized_permissions: [],
        source: allQuickAction ? 'quick_action' : 'manual',
      }
    }

    if (emphasis.value.length > 0) {
      payload.expertise_emphasis = [...emphasis.value]
    }

    return payload
  })

  function setIntent(nextIntent: IntentType) {
    if (intent.value === nextIntent) return
    intent.value = nextIntent
    stageOverrides.value = {}
  }

  function addContextFile(file: Omit<ContextFile, 'id'>, source: ContextFile['source'] = 'manual') {
    const value = file.value.trim()
    if (!value) return
    const exists = contextFiles.value.some(
      (item) => item.type === file.type && item.value === value && item.mount_id === file.mount_id,
    )
    if (exists) return
    contextFiles.value.push({
      ...file,
      id: createId(),
      value,
      label: file.label.trim() || value,
      source,
    } as ContextFile)
  }

  function toggleContextFile(id: string) {
    const file = contextFiles.value.find((item) => item.id === id)
    if (file) file.active = !file.active
  }

  function removeContextFile(id: string) {
    contextFiles.value = contextFiles.value.filter((item) => item.id !== id)
  }

  // ── 关联技能（L3：快捷方式联动预授权的 Skill）──────────────────────
  function addSkill(name: string, source: LinkedSkill['source'] = 'manual') {
    const normalized = name.trim()
    if (!normalized) return
    if (skills.value.some((item) => item.name === normalized)) return
    skills.value = [...skills.value, { name: normalized, source }]
  }

  function removeSkill(name: string) {
    skills.value = skills.value.filter((item) => item.name !== name)
  }

  function clearSkills() {
    skills.value = []
  }

  function setEmphasis(dimensions: string[]) {
    emphasis.value = Array.isArray(dimensions) ? dimensions.filter(Boolean).map(String) : []
  }

  /**
   * L3 预设应用：整体替换（而非累积追加）。
   * 先撤销上一预设带来的 intent 无关项（skills / contextFiles 中 source==='quick_action'），
   * 再应用新预设的意图 / 技能 / 上下文 / 强调维度。用户手动添加的项保留。
   */
  function applyPreset(action: PipelineQuickAction) {
    skills.value = skills.value.filter((s) => s.source !== 'quick_action')
    contextFiles.value = contextFiles.value.filter((f) => f.source !== 'quick_action')

    if (action.intent) setIntent(action.intent)
    for (const cf of action.context_files ?? []) {
      addContextFile(
        {
          type: cf.type,
          value: cf.value,
          label: cf.label?.trim() || cf.value,
          active: true,
          mount_id: cf.mount_id,
        },
        'quick_action',
      )
    }
    for (const skill of action.skills ?? []) {
      addSkill(skill, 'quick_action')
    }
    setEmphasis(action.emphasis ?? [])
    appliedPresetId.value = action.id
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
    [intent, contextFiles, stageOverrides, skills, emphasis, appliedPresetId],
    () => {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          intent: intent.value,
          contextFiles: contextFiles.value,
          stageOverrides: stageOverrides.value,
          skills: skills.value,
          emphasis: emphasis.value,
          appliedPresetId: appliedPresetId.value,
        }),
      )
    },
    { deep: true },
  )

  return {
    intent,
    contextFiles,
    stageOverrides,
    skills,
    emphasis,
    appliedPresetId,
    activeContextFiles,
    activeStages,
    chatPayload,
    setIntent,
    addContextFile,
    toggleContextFile,
    removeContextFile,
    addSkill,
    removeSkill,
    clearSkills,
    setEmphasis,
    applyPreset,
    isStageEnabled,
    toggleStage,
    buildChatPayload,
  }
})
