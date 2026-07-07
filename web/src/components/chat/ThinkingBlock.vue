<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = defineProps<{
  step: {
    type: 'thinking'
    content: string
    streaming: boolean
    duration_ms?: number
  }
}>()

// streaming 时展开；完成后保持展开，让用户主动折叠
// 历史消息（初始非 streaming）默认折叠
const expanded = ref(props.step.streaming)
const thinkingDone = computed(() => !props.step.streaming)
watch(
  () => props.step.streaming,
  (streaming) => {
    if (streaming) expanded.value = true  // 开始思考时展开
    // 思考完成后不自动折叠
  },
)

const displayContent = computed(() => {
  return props.step.content || '思考中…'
})
</script>

<template>
  <div
    class="thinking-block"
    :class="{ 'thinking-block--done': thinkingDone }"
  >
    <button class="thinking-block__toggle" @click="expanded = !expanded">
      <svg
        width="14" height="14" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2"
        :style="{ transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform .2s' }"
      >
        <polyline points="9 18 15 12 9 6" />
      </svg>

      <span class="thinking-block__label">
        {{ thinkingDone ? '思考过程' : '思考中…' }}
      </span>

      <span v-if="!thinkingDone" class="thinking-block__spinner" />

      <span v-if="thinkingDone && step.duration_ms" class="thinking-block__duration">
        {{ step.duration_ms }}ms
      </span>
    </button>

    <transition name="slide">
      <div v-show="expanded" class="thinking-block__content">
        {{ displayContent }}
      </div>
    </transition>
  </div>
</template>

<style scoped lang="scss">
.thinking-block {
  margin-bottom: 10px;
  border: 1px solid #e0e0f0;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f8ff;

  &--done {
    border-color: #c7d2fe;
    background: #f5f3ff;
  }
}

.thinking-block__toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #6366f1;
  font-weight: 500;
  text-align: left;

  &:hover { background: rgba(99, 102, 241, .06); }
}

.thinking-block__label {
  flex: 1;
}

.thinking-block__spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #c7d2fe;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

.thinking-block__duration {
  font-size: 11px;
  color: #9ca3af;
}

.thinking-block__content {
  padding: 10px 14px 12px;
  border-top: 1px solid #e0e0f0;
  font-size: 13px;
  color: #6b7280;
  font-style: italic;
  line-height: 1.6;
  white-space: pre-wrap;
}

// ── 折叠动画 ───────────────────────────────────────────────────
.slide-enter-active,
.slide-leave-active {
  transition: max-height .25s ease, opacity .25s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
