import request from '@/api/request'
import type { Artifact } from '@/types'

export const artifactsApi = {
  get: (artifactId: string) => request.get<Artifact>(`/artifacts/${artifactId}`),

  update: (artifactId: string, data: Partial<Artifact>) =>
    request.patch<Artifact>(`/artifacts/${artifactId}`, data),

  delete: (artifactId: string) => request.delete(`/artifacts/${artifactId}`),
}
