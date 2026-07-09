import { usePipelineStore } from '@/stores/pipeline'
import type { ChatIntentType, PipelineQuickAction } from '@/types'

export type IntentType = ChatIntentType

export interface Stage {
  id: string
  label: string
  optional?: boolean
}

export interface IntentConfig {
  stages: Stage[]
  skippedStages: string[]
  quickActions: PipelineQuickAction[]
  placeholder: string
}

const emptyConfig: IntentConfig = {
  stages: [],
  skippedStages: [],
  quickActions: [],
  placeholder: '描述当前项目里的开发需求...',
}

export function usePipeline() {
  const pipelineStore = usePipelineStore()

  function getConfig(intent: IntentType): IntentConfig {
    const definition = pipelineStore.catalogForIntent(intent)
    if (!definition) return emptyConfig
    return {
      stages: definition.stages.map((stage) => ({
        id: stage.stage_id,
        label: stage.stage_name,
        optional: !stage.required,
      })),
      skippedStages: [],
      quickActions: definition.default_actions,
      placeholder: definition.placeholder,
    }
  }

  const intentLabels: Record<IntentType, { label: string; icon: string }> = {
    new_feature: { label: '全新功能', icon: '✨' },
    iteration: { label: '迭代优化', icon: '🔄' },
    ui_adjust: { label: 'UI 调整', icon: '🎨' },
    bug_fix: { label: 'Bug 修复', icon: '🐛' },
  }

  return {
    getConfig,
    intentLabels,
  }
}
