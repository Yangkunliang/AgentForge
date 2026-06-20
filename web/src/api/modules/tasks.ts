import request from '../request'
import type { Task, CreateTaskForm, SubTask, TaskFeedback, PaginatedResponse } from '@/types'

export interface TaskListParams {
  page?: number
  per_page?: number
  status?: string
  priority?: string
}

export const tasksApi = {
  list: (params?: TaskListParams) => {
    return request.get<PaginatedResponse<Task>>('/tasks', { params })
  },

  create: (data: CreateTaskForm) => {
    return request.post<{ task_id: string; status: string; trace_id: string }>('/tasks', data)
  },

  get: (taskId: string) => {
    return request.get<{
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
    }>(`/tasks/${taskId}`)
  },

  cancel: (taskId: string) => {
    return request.post<{ task_id: string; status: string }>(`/tasks/${taskId}/cancel`)
  },

  feedback: (taskId: string, data: TaskFeedback) => {
    return request.post<{ task_id: string; feedback_recorded: boolean }>(
      `/tasks/${taskId}/feedback`,
      data
    )
  },

  stream: (taskId: string) => {
    return `/api/v1/tasks/${taskId}/stream`
  },
}
