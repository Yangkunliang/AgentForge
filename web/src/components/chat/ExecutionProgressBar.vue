<script setup lang="ts">
/** ExecutionProgressBar — indeterminate 进度条，仅 streaming=true 时显示 */
defineProps<{
  streaming: boolean
  color?: string
}>()
</script>

<template>
  <div v-if="streaming" class="execution-progress">
    <div class="execution-progress__bar" />
  </div>
</template>

<style scoped lang="scss">
.execution-progress {
  margin-bottom: 8px;
  height: 2px;
  background: #e5e7eb;
  border-radius: 1px;
  overflow: hidden;
}

.execution-progress__bar {
  height: 100%;
  width: 30%;
  background: var(--progress-color, #6366f1);
  border-radius: 1px;
  animation: progress-slide 1.4s ease-in-out infinite;
}

@keyframes progress-slide {
  0%   { transform: translateX(-100%); }
  50%  { transform: translateX(100%); }
  100% { transform: translateX(100%); }
}
</style>
