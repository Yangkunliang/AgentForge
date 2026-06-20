import request from '../request'
import type { DashboardStats } from '@/types'

export const dashboardApi = {
  get: () => {
    return request.get<DashboardStats>('/dashboard')
  },
}
