<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { SSEEvent } from '@/types'

const props = defineProps<{
  events: SSEEvent[]
}>()

const logContainer = ref<HTMLElement | null>(null)

function getEventClass(event: SSEEvent): string {
  switch (event.event) {
    case 'task_started':
    case 'task_completed':
      return 'log-line--success'
    case 'task_failed':
      return 'log-line--error'
    case 'skill_called':
    case 'skill_result':
      return 'log-line--warning'
    default:
      return 'log-line--info'
  }
}

function getEventMessage(event: SSEEvent): string {
  switch (event.event) {
    case 'task_started':
      return `[${event.event}] 任务开始执行`
    case 'sub_task_created':
      return `[${event.event}] 创建子任务: ${event.data.description}`
    case 'bid_received':
      return `[${event.event}] Agent 竞标: ${event.data.agent_name}`
    case 'agent_selected':
      return `[${event.event}] 选中 Agent: ${event.data.agent_name}`
    case 'message':
      return `[${event.event}] ${event.data.content}`
    case 'skill_called':
      return `[${event.event}] 调用 Skill: ${event.data.skill_name}`
    case 'skill_result':
      return `[${event.event}] Skill 结果: ${event.data.success ? '成功' : '失败'}`
    case 'sub_task_completed':
      return `[${event.event}] 子任务完成`
    case 'task_completed':
      return `[${event.event}] 任务完成`
    case 'task_failed':
      return `[${event.event}] 任务失败: ${event.data.error}`
    default:
      return `[${event.event}] ${JSON.stringify(event.data)}`
  }
}

watch(
  () => props.events.length,
  async () => {
    await nextTick()
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  }
)
</script>

<template>
  <div ref="logContainer" class="log-container">
    <div v-if="events.length === 0" class="log-line log-line--info">
      等待事件...
    </div>
    <div
      v-for="(event, index) in events"
      :key="index"
      class="log-line"
      :class="getEventClass(event)"
    >
      {{ getEventMessage(event) }}
    </div>
  </div>
</template>

<style scoped lang="scss">
.log-container {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: $spacing-md;
  border-radius: $border-radius-sm;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;

  .log-line {
    white-space: pre-wrap;
    word-break: break-all;

    &--info {
      color: #d4d4d4;
    }

    &--success {
      color: #67c23a;
    }

    &--warning {
      color: #e6a23c;
    }

    &--error {
      color: #f56c6c;
    }
  }
}
</style>
