<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import ThinkingBlock from './ThinkingBlock.vue'
import ToolCallCard from './ToolCallCard.vue'
import CodeExecutionCard from './CodeExecutionCard.vue'

const props = defineProps<{
  steps: import('@/types').ExecutionStep[]
  streaming: boolean
}>()

// streaming 时自动展开；完成后保持展开，让用户主动折叠
// 只有历史消息（初始就是非 streaming 状态）才默认折叠
const collapsed = ref(!props.streaming)
const stepCount = computed(() => props.steps.length)
watch(
  () => props.streaming,
  (streaming) => {
    if (streaming) collapsed.value = false  // 开始时展开
    // 结束时不自动折叠，让用户自己决定
  },
)

// 按步骤类型分发渲染组件
function renderStep(step: import('@/types').ExecutionStep, index: number) {
  switch (step.type) {
    case 'thinking':
      return ThinkingBlock
    case 'tool_call':
      return ToolCallCard
    case 'code_execution':
      return CodeExecutionCard
  }
}
</script>

<template>
  <div v-if="steps && steps.length > 0" class="execution-step-list">
    <!-- 折叠 header -->
    <button class="execution-step-list__toggle" @click="collapsed = !collapsed">
      <svg
        width="14" height="14" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2"
        :style="{ transform: collapsed ? '' : 'rotate(90deg)', transition: 'transform .2s' }"
      >
        <polyline points="9 18 15 12 9 6" />
      </svg>
      <span class="execution-step-list__label">执行过程 · {{ stepCount }}步</span>
      <span v-if="streaming" class="execution-step-list__spinner" />
    </button>

    <!-- 步骤列表 -->
    <transition name="slide">
      <div v-show="!collapsed" class="execution-step-list__content">
        <div
          v-for="(step, idx) in steps"
          :key="idx"
          class="execution-step-list__item"
          :class="{ 'execution-step-list__item--first': idx === 0 }"
        >
          <!-- 连接线：圆点 + 竖线 -->
          <div class="execution-step-list__connector" />

          <!-- 对应卡片组件 -->
          <component
            :is="renderStep(step, idx)"
            :step="step"
          />
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped lang="scss">
.execution-step-list {
  margin-bottom: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #f9fafb;
}

.execution-step-list__toggle {
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

.execution-step-list__label {
  flex: 1;
}

.execution-step-list__spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #c7d2fe;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

.execution-step-list__content {
  padding: 8px 12px 12px;
  border-top: 1px solid #e5e7eb;
}

.execution-step-list__item {
  position: relative;
  padding-left: 20px;
  margin-bottom: 6px;

  &:last-child { margin-bottom: 0; }

  &--first { margin-top: 0; }
}

// 连接线：圆点 + 竖线
.execution-step-list__connector {
  position: absolute;
  left: 5px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e5e7eb;

  &::before {
    content: '';
    position: absolute;
    top: 6px;
    left: -3px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6366f1;
    border: 2px solid #f9fafb;
  }
}

// 折叠动画
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
