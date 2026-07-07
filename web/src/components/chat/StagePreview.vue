<script setup lang="ts">
import type { IntentType } from '@/composables/usePipeline'
import { usePipeline } from '@/composables/usePipeline'
import { useAdvancedSettingsStore } from '@/stores/advancedSettings'
import { computed } from 'vue'

const props = defineProps<{
  intent: IntentType
}>()

const { getConfig } = usePipeline()
const advancedSettings = useAdvancedSettingsStore()

const config = computed(() => getConfig(props.intent))

function isSkipped(stageId: string): boolean {
  return !advancedSettings.isStageEnabled(stageId)
}

function toggleStage(stage: { id: string; optional?: boolean }) {
  if (!stage.optional) return
  advancedSettings.toggleStage(stage.id)
}
</script>

<template>
  <div class="stage-preview">
    <div class="stage-list">
      <template v-for="(stage, index) in config.stages" :key="stage.id">
        <div
          class="stage-pill"
          :class="{ optional: stage.optional, skipped: isSkipped(stage.id) }"
          :title="stage.optional ? '点击跳过或恢复此阶段' : '此阶段为必需步骤'"
          @click="toggleStage(stage)"
        >
          <span class="stage-label">{{ stage.label }}</span>
          <span v-if="stage.optional" class="optional-mark">*</span>
        </div>
        <svg v-if="index < config.stages.length - 1" class="stage-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
      </template>
    </div>
    <div v-if="config.skippedStages.length > 0" class="skipped-stages">
      <span class="skipped-label">跳过：</span>
      <span v-for="stage in config.skippedStages" :key="stage" class="skipped-item">{{ stage }}</span>
    </div>
    <div v-if="Object.keys(advancedSettings.stageOverrides).length > 0" class="skipped-stages">
      <span class="skipped-label">用户调整：</span>
      <span
        v-for="(_enabled, stageId) in advancedSettings.stageOverrides"
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

  &.skipped {
    background: #f1f5f9;
    border-color: #e2e8f0;
    color: #94a3b8;
    text-decoration: line-through;
    opacity: 0.72;
  }
}

.optional-mark {
  font-size: 10px;
  opacity: 0.7;
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
