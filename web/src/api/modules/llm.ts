import request from '@/api/request'

export interface LLMProvider {
  id: string
  provider_key: string
  name: string
  base_url?: string | null
  status: 'active' | 'inactive'
  created_at: string
  updated_at: string
}

export interface LLMModel {
  id: string
  provider_id: string
  provider_key?: string | null
  model_key: string
  name: string
  capabilities: string[]
  context_window?: number | null
  input_price_per_1m?: number | null
  output_price_per_1m?: number | null
  status: 'active' | 'inactive'
  created_at: string
  updated_at: string
}

export interface LLMCredential {
  id: string
  provider_id: string
  provider_key?: string | null
  name: string
  secret_set: boolean
  masked_secret: string
  active: boolean
  created_at: string
  updated_at: string
}

export interface LLMRoute {
  id: string
  route_key: string
  name: string
  provider_id: string
  provider_key?: string | null
  model_id: string
  model_name?: string | null
  credential_id?: string | null
  credential_name?: string | null
  temperature: number
  max_tokens: number
  timeout_seconds: number
  fallback_route_keys: string[]
  active: boolean
  created_at: string
  updated_at: string
}

export interface LLMConfig {
  api_key_set: boolean
  default_model: string
  default_temperature: number
  max_tokens: number
  model_routes: Record<string, string>
  providers: LLMProvider[]
  models: LLMModel[]
  credentials: LLMCredential[]
  routes: LLMRoute[]
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

  createProvider: (body: {
    provider_key: string
    name: string
    base_url?: string
    status?: 'active' | 'inactive'
  }) => request.post<LLMProvider>('/llm/providers', body),

  createModel: (body: {
    provider_id: string
    model_key: string
    name: string
    capabilities?: string[]
    context_window?: number
    input_price_per_1m?: number
    output_price_per_1m?: number
    status?: 'active' | 'inactive'
  }) => request.post<LLMModel>('/llm/models', body),

  createCredential: (body: {
    provider_id: string
    name: string
    secret: string
    active?: boolean
  }) => request.post<LLMCredential>('/llm/credentials', body),

  createRoute: (body: {
    route_key: string
    name: string
    provider_id: string
    model_id: string
    credential_id?: string | null
    temperature?: number
    max_tokens?: number
    timeout_seconds?: number
    fallback_route_keys?: string[]
    active?: boolean
  }) => request.post<LLMRoute>('/llm/routes', body),
}
