import request from '../request'
import type { ExportTask, CreateExportForm } from '@/types'

export const exportsApi = {
  list: () => {
    return request.get<{ total: number; items: ExportTask[] }>('/exports')
  },

  create: (data: CreateExportForm) => {
    return request.post<{
      export_id: string
      status: string
      total_records: number
      estimated_size_mb: number
    }>('/exports', data)
  },

  getStatus: (exportId: string) => {
    return request.get<ExportTask>(`/exports/${exportId}`)
  },

  download: (exportId: string) => {
    return `/api/v1/exports/${exportId}/download`
  },
}
