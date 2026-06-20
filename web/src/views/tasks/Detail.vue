<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { useSSE } from '@/composables'
import LiveLog from '@/components/tasks/LiveLog.vue'
import TaskProgress from '@/components/tasks/TaskProgress.vue'

const props = defineProps<{ id: string }>()

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

const taskId = computed(() => props.id || route.params.id as string)

const { connected, connect, disconnect } = useSSE(taskId.value, {
  onConnect: () => {
    console.log('SSE connected')
  },
  onDisconnect: () => {
    console.log('SSE disconnected')
  },
})

onMounted(async () => {
  await taskStore.fetchTask(taskId.value)
  connect()
})

onUnmounted(() => {
  disconnect()
  taskStore.clearCurrentTask()
})

function getStatusTagType(status: string): string {
  const map: Record<string, string> = {
    pending: 'warning',
    processing: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

async function handleCancel() {
  await taskStore.fetchTask(taskId.value)
}
</script>

<template>
  <div class="task-detail">
    <div class="page-header">
      <el-button @click="router.back()">返回</el-button>
      <el-button
        v-if="taskStore.currentTask?.status === 'pending'"
        type="danger"
        @click="handleCancel"
      >
        取消任务
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="16">
        <div class="card">
          <div class="card__header">
            任务详情
            <el-tag :type="getStatusTagType(taskStore.currentTask?.status ?? '')" class="ml-2">
              {{ taskStore.currentTask?.status }}
            </el-tag>
          </div>
          <div class="task-info">
            <div class="info-item">
              <span class="label">ID:</span>
              <span class="value">{{ taskStore.currentTask?.task_id }}</span>
            </div>
            <div class="info-item">
              <span class="label">描述:</span>
              <p class="description">{{ taskStore.currentTask?.description }}</p>
            </div>
            <div class="info-item">
              <span class="label">费用:</span>
              <span class="value">${{ (taskStore.currentTask?.total_cost_usd ?? 0).toFixed(4) }}</span>
            </div>
            <div class="info-item">
              <span class="label">创建时间:</span>
              <span class="value">{{ formatDate(taskStore.currentTask?.created_at ?? '') }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card__header">实时日志</div>
          <div class="connection-status">
            <el-tag :type="connected ? 'success' : 'danger'" size="small">
              {{ connected ? '已连接' : '未连接' }}
            </el-tag>
          </div>
          <LiveLog :events="taskStore.sseEvents" />
        </div>
      </el-col>

      <el-col :span="8">
        <div class="card">
          <div class="card__header">执行进度</div>
          <TaskProgress :task="taskStore.currentTask" :events="taskStore.sseEvents" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
}

.ml-2 {
  margin-left: $spacing-sm;
}

.task-info {
  .info-item {
    margin-bottom: $spacing-md;

    .label {
      font-weight: 600;
      color: #606266;
      margin-right: $spacing-sm;
    }

    .description {
      margin: $spacing-sm 0 0;
      color: #303133;
    }
  }
}

.connection-status {
  margin-bottom: $spacing-md;
}
</style>
