import request from '@/api/request'

export interface LLMConfig {
  api_key_set: boolean
  default_model: string
  default_temperature: number
  max_tokens: number
  model_routes: Record<string, string>
}

export const llmApi = {
  get: () => request.get<LLMConfig>('/llm'),

  update: (body: {
    default_model: string
    default_temperature: number
    max_tokens: number
    model_routes?: Record<string, string>
    api_key?: string
    vision_model?: string
    image_gen_model?: string
  }) => request.post('/llm', body),
}
