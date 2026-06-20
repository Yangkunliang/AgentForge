import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tasksApi, type TaskListParams } from '@/api/modules/tasks'
import type { Task, SubTask, SSEEvent } from '@/types'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const currentTask = ref<{
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
  } | null>(null)
  const sseEvents = ref<SSEEvent[]>([])
  const loading = ref(false)
  const pagination = ref({
    page: 1,
    per_page: 20,
    total: 0,
  })

  const taskStats = computed(() => {
    const stats = { pending: 0, processing: 0, completed: 0, failed: 0, cancelled: 0 }
    tasks.value.forEach((task) => {
      if (task.status in stats) {
        stats[task.status as keyof typeof stats]++
      }
    })
    return stats
  })

  async function fetchTasks(params?: TaskListParams) {
    loading.value = true
    try {
      const { data } = await tasksApi.list({
        page: pagination.value.page,
        per_page: pagination.value.per_page,
        ...params,
      })
      tasks.value = data.items
      pagination.value.total = data.total
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(taskId: string) {
    loading.value = true
    try {
      const { data } = await tasksApi.get(taskId)
      currentTask.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  function handleSSEEvent(event: SSEEvent) {
    sseEvents.value.push(event)

    // 根据事件类型更新 currentTask
    if (currentTask.value) {
      switch (event.event) {
        case 'sub_task_created':
          if (event.data.sub_task) {
            currentTask.value.sub_tasks.push(event.data.sub_task as SubTask)
          }
          break
        case 'sub_task_completed':
          if (event.data.sub_task_id) {
            const subTask = currentTask.value.sub_tasks.find(
              (st) => st.id === event.data.sub_task_id
            )
            if (subTask) {
              subTask.status = 'completed'
              subTask.result = event.data.result as string
            }
          }
          break
        case 'task_completed':
          currentTask.value.status = 'completed'
          currentTask.value.result = event.data.result as string
          break
        case 'task_failed':
          currentTask.value.status = 'failed'
          break
      }
    }
  }

  function clearEvents() {
    sseEvents.value = []
  }

  function clearCurrentTask() {
    currentTask.value = null
    sseEvents.value = []
  }

  return {
    tasks,
    currentTask,
    sseEvents,
    loading,
    pagination,
    taskStats,
    fetchTasks,
    fetchTask,
    handleSSEEvent,
    clearEvents,
    clearCurrentTask,
  }
})
