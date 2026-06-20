<script setup lang="ts">
import { computed } from 'vue'
import type { SSEEvent, SubTask } from '@/types'

const props = defineProps<{
  task: {
    task_id: string
    description: string
    status: string
    priority: string
    result?: string
    total_cost_usd?: number
    created_at: string
    completed_at?: string
    trace_id: string
    sub_tasks: SubTask[]
  } | null
  events: SSEEvent[]
}>()

const completedSubTasks = computed(() => {
  return props.events.filter((e) => e.event === 'sub_task_completed').length
})

const totalSubTasks = computed(() => {
  return props.task?.sub_tasks.length ?? 0
})

const progress = computed(() => {
  if (!totalSubTasks.value) return 0
  return Math.round((completedSubTasks.value / totalSubTasks.value) * 100)
})

const recentBids = computed(() => {
  return props.events
    .filter((e) => e.event === 'bid_received')
    .slice(-3)
    .map((e) => e.data.agent_name as string)
})
</script>

<template>
  <div class="task-progress">
    <el-progress
      :percentage="progress"
      :status="task?.status === 'completed' ? 'success' : undefined"
    />

    <div class="progress-info">
      <span>子任务进度: {{ completedSubTasks }}/{{ totalSubTasks }}</span>
    </div>

    <div v-if="recentBids.length > 0" class="recent-bids">
      <div class="section-title">最近竞标</div>
      <el-tag v-for="name in recentBids" :key="name" size="small" class="bid-tag">
        {{ name }}
      </el-tag>
    </div>

    <div v-if="task?.result" class="task-result">
      <div class="section-title">结果</div>
      <div class="result-content">{{ task.result }}</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.task-progress {
  .progress-info {
    margin-top: $spacing-sm;
    font-size: 13px;
    color: #909399;
  }

  .recent-bids {
    margin-top: $spacing-lg;

    .section-title {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: $spacing-sm;
    }

    .bid-tag {
      margin-right: $spacing-xs;
      margin-bottom: $spacing-xs;
    }
  }

  .task-result {
    margin-top: $spacing-lg;

    .section-title {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: $spacing-sm;
    }

    .result-content {
      background: #f5f7fa;
      padding: $spacing-md;
      border-radius: $border-radius-sm;
      font-size: 13px;
      max-height: 200px;
      overflow-y: auto;
    }
  }
}
</style>
