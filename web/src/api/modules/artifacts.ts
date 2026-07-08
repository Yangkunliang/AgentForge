import request from '@/api/request'
import type { Artifact, DeliveryApplyPayload, DeliveryResponse, DeliveryTargetPayload } from '@/types'

export const artifactsApi = {
  get: (artifactId: string) => request.get<Artifact>(`/artifacts/${artifactId}`),

  update: (artifactId: string, data: Partial<Artifact>) =>
    request.patch<Artifact>(`/artifacts/${artifactId}`, data),

  previewDelivery: (artifactId: string, data: DeliveryTargetPayload) =>
    request.post<DeliveryResponse>(`/artifacts/${artifactId}/delivery/preview`, data),

  applyDelivery: (artifactId: string, data: DeliveryApplyPayload) =>
    request.post<DeliveryResponse>(`/artifacts/${artifactId}/delivery/apply`, data),

  exportDeliveryReport: (artifactId: string) =>
    request.get<string>(`/artifacts/${artifactId}/delivery/report`, {
      responseType: 'text',
    }),

  delete: (artifactId: string) => request.delete(`/artifacts/${artifactId}`),
}
