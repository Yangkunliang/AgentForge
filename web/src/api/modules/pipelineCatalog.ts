import request from '@/api/request'
import type { ChatIntentType, PipelineCatalogResponse, PipelineIntentCatalog } from '@/types'

export const pipelineCatalogApi = {
  list: () => request.get<PipelineCatalogResponse>('/pipeline/catalog'),

  get: (intentType: ChatIntentType) =>
    request.get<PipelineIntentCatalog>(`/pipeline/catalog/${intentType}`),
}
