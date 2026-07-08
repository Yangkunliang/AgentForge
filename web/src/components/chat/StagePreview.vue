<script setup lang="ts">
import type { IntentType } from '@/composables/usePipeline'
import { usePipeline } from '@/composables/usePipeline'
import { useAdvancedSettingsStore } from '@/stores/advancedSettings'
import { usePipelineStore } from '@/stores/pipeline'
import type { PipelineRun, PipelineStageStatus } from '@/types'
import { computed } from 'vue'

const props = defineProps<{
  intent: IntentType
  pipelineRun?: PipelineRun | null
}>()

const { getConfig } = usePipeline()
const advancedSettings = useAdvancedSettingsStore()
const pipelineStore = usePipelineStore()

const config = computed(() => getConfig(props.intent))

type StageView = {
  id: string
  label: string
  optional: boolean
  status: PipelineStageStatus
}

const stages = computed<StageView[]>(() => {
  if (props.pipelineRun) {
    return [...props.pipelineRun.stages]
      .sort((left, right) => left.order_index - right.order_index)
      .map((stage) => ({
        id: stage.stage_id,
        label: stage.stage_name,
        optional: !stage.required,
        status: stage.status,
      }))
  }

  return config.value.stages.map((stage) => ({
    id: stage.id,
    label: stage.label,
    optional: Boolean(stage.optional),
    status: advancedSettings.isStageEnabled(stage.id) ? 'pending' : 'skipped',
  }))
})

const skippedStageNames = computed(() => {
  if (props.pipelineRun) {
    return stages.value
      .filter((stage) => stage.status === 'skipped')
      .map((stage) => stage.label)
  }

  const overridden = config.value.stages
    .filter((stage) => !advancedSettings.isStageEnabled(stage.id))
    .map((stage) => stage.label)
  return [...config.value.skippedStages, ...overridden]
})

const localOverrideStageIds = computed(() =>
  props.pipelineRun ? [] : Object.keys(advancedSettings.stageOverrides),
)

const statusLabels: Partial<Record<PipelineStageStatus, string>> = {
  running: '运行中',
  waiting_confirmation: '待确认',
  completed: '完成',
  skipped: '跳过',
  failed: '失败',
}

function isSkipped(stage: StageView): boolean {
  return stage.status === 'skipped'
}

function isCurrent(stage: StageView): boolean {
  return props.pipelineRun?.current_stage_id === stage.id
}

async function toggleStage(stage: StageView) {
  if (!stage.optional) return
  if (!props.pipelineRun) {
    advancedSettings.toggleStage(stage.id)
    return
  }

  if (pipelineStore.mutatingStageId) return

  if (isSkipped(stage)) {
    await pipelineStore.restoreStage(stage.id)
  } else {
    await pipelineStore.skipStage(stage.id)
  }
}

function stageTitle(stage: StageView): string {
  if (!stage.optional) return '此阶段为必需步骤'
  return isSkipped(stage) ? '点击恢复此阶段' : '点击跳过此阶段'
}
</script>

<template>
  <div class="stage-preview">
    <div class="stage-list">
      <template v-for="(stage, index) in stages" :key="stage.id">
        <div
          class="stage-pill"
          :class="{
            optional: stage.optional,
            skipped: isSkipped(stage),
            running: stage.status === 'running',
            completed: stage.status === 'completed',
            failed: stage.status === 'failed',
            current: isCurrent(stage),
            mutating: pipelineStore.mutatingStageId === stage.id,
          }"
          :title="stageTitle(stage)"
          @click="toggleStage(stage)"
        >
          <span class="stage-label">{{ stage.label }}</span>
          <span v-if="stage.optional" class="optional-mark">*</span>
          <span v-if="statusLabels[stage.status]" class="stage-status">
            {{ statusLabels[stage.status] }}
          </span>
        </div>
        <svg v-if="index < stages.length - 1" class="stage-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
      </template>
    </div>
    <div v-if="skippedStageNames.length > 0" class="skipped-stages">
      <span class="skipped-label">跳过：</span>
      <span v-for="stage in skippedStageNames" :key="stage" class="skipped-item">{{ stage }}</span>
    </div>
    <div v-if="localOverrideStageIds.length > 0" class="skipped-stages">
      <span class="skipped-label">用户调整：</span>
      <span
        v-for="stageId in localOverrideStageIds"
        :key="stageId"
        class="skipped-item"
      >
        {{ stageId }}
      </span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stage-preview {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stage-list {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.stage-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 4px 9px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  font-size: 11px;
  color: #475569;
  font-weight: 500;
  transition: all 0.15s;
  cursor: default;

  &:hover {
    background: #fff;
    border-color: #cbd5e1;
  }

  &.optional {
    background: #fef3c7;
    border-color: #fde68a;
    color: #b45309;
    cursor: pointer;
  }

  &.current {
    border-color: #93c5fd;
    box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.12);
  }

  &.running {
    background: #eff6ff;
    border-color: #bfdbfe;
    color: #2563eb;
  }

  &.completed {
    background: #ecfdf5;
    border-color: #bbf7d0;
    color: #047857;
  }

  &.failed {
    background: #fef2f2;
    border-color: #fecaca;
    color: #b91c1c;
  }

  &.skipped {
    background: #f1f5f9;
    border-color: #e2e8f0;
    color: #94a3b8;
    text-decoration: line-through;
    opacity: 0.72;
  }

  &.mutating {
    pointer-events: none;
    opacity: 0.58;
  }
}

.optional-mark {
  font-size: 10px;
  opacity: 0.7;
}

.stage-status {
  font-size: 10px;
  color: currentColor;
  opacity: 0.78;
  text-decoration: none;
}

.stage-arrow {
  color: #cbd5e1;
  flex-shrink: 0;
}

.skipped-stages {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.skipped-label {
  font-size: 10px;
  color: #94a3b8;
}

.skipped-item {
  font-size: 10px;
  color: #94a3b8;
  padding: 2px 6px;
  background: #f1f5f9;
  border-radius: 4px;
  text-decoration: line-through;
  text-decoration-color: #cbd5e1;

}
</style>
