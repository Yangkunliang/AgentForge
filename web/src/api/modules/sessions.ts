import request from '@/api/request'
import type { Session, ChatMessage } from '@/types'

export const sessionsApi = {
  list: () => request.get<Session[]>('/sessions'),

  create: () => request.post<Session>('/sessions', {}),

  rename: (id: string, title: string) =>
    request.patch<Session>(`/sessions/${id}`, { title }),

  delete: (id: string) => request.delete(`/sessions/${id}`),

  messages: (id: string) => request.get<ChatMessage[]>(`/sessions/${id}/messages`),

  chat: (id: string, content: string) =>
    request.post<{ message_id: string; task_id: string }>(`/sessions/${id}/chat`, { content }),
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
