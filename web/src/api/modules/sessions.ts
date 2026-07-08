import request from '@/api/request'
import type { Session, ChatMessage, ChatAdvancedPayload, ChatResponse } from '@/types'
import { projectsApi } from '@/api/modules/projects'

export const sessionsApi = {
  list: (projectId?: string | null) =>
    projectId ? projectsApi.listSessions(projectId) : request.get<Session[]>('/sessions'),

  create: (projectId?: string | null, intentType?: string | null) =>
    projectId
      ? projectsApi.createSession(projectId, { intent_type: intentType ?? null })
      : request.post<Session>('/sessions', {}),

  rename: (id: string, title: string) =>
    request.patch<Session>(`/sessions/${id}`, { title }),

  delete: (id: string) => request.delete(`/sessions/${id}`),

  messages: (id: string) => request.get<ChatMessage[]>(`/sessions/${id}/messages`),

  chat: (id: string, content: string, advanced?: ChatAdvancedPayload) =>
    request.post<ChatResponse>(`/sessions/${id}/chat`, {
      content,
      ...advanced,
    }),
}

export const uploadApi = {
  image: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<{ url: string; filename: string; size: number }>('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
