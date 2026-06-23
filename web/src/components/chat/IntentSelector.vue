<script setup lang="ts">
import type { IntentType } from '@/composables/usePipeline'
import { usePipeline } from '@/composables/usePipeline'

defineProps<{
  modelValue: IntentType
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: IntentType): void
}>()

const { intentLabels } = usePipeline()

const intents: IntentType[] = ['new_feature', 'iteration', 'ui_adjust', 'bug_fix']

function selectIntent(intent: IntentType) {
  emit('update:modelValue', intent)
}
</script>

<template>
  <div class="intent-selector">
    <button
      v-for="intent in intents"
      :key="intent"
      class="intent-btn"
      :class="{ active: modelValue === intent }"
      @click="selectIntent(intent)"
    >
      <span class="intent-icon">{{ intentLabels[intent].icon }}</span>
      <span class="intent-label">{{ intentLabels[intent].label }}</span>
    </button>
  </div>
</template>

<style scoped lang="scss">
.intent-selector {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.intent-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: #cbd5e1;
    background: #fff;
    color: #334155;
  }

  &.active {
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border-color: #3b82f6;
    color: #1d4ed8;
    font-weight: 600;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
  }
}

.intent-icon {
  font-size: 13px;
}

.intent-label {
  white-space: nowrap;
}
</style>
