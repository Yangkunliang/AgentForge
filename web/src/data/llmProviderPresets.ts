/**
 * LLM 服务商精选预设目录
 *
 * 用途：让 /settings/llm 的配置尽量「选择式」而非手工填写。
 * - 选服务商即自动带出默认 Base URL 与热门模型清单（勾选即可批量添加）。
 * - 覆盖国际 / 国内 / 本地·自建三类常见 OpenAI 兼容端点。
 *
 * 说明：LLM 服务商端点高度标准化（大多 OpenAI 兼容），故用精选目录而非实时市场。
 * 若后续要做「市场」，可把本目录挪到后端 /llm/provider-presets 端点，变成可远端更新的注册表。
 */

export type ModelCapability = 'text' | 'code' | 'vision' | 'image' | 'reasoning' | 'audio'

export interface PresetModel {
  key: string
  name: string
  capabilities: ModelCapability[]
  context_window?: number
}

export interface ProviderPreset {
  /** 与后端 provider_key 一致（新增时用作 key，已存在则提示） */
  key: string
  name: string
  group: '国际' | '国内' | '本地 / 自建'
  /** 默认 Base URL（用户可改） */
  base_url: string
  /** 文档 / 申请入口 */
  docs_url?: string
  /** API Key 输入框占位提示 */
  key_hint?: string
  models: PresetModel[]
}

const K = (c: ModelCapability[]) => c

export const PROVIDER_PRESETS: ProviderPreset[] = [
  // ── 国际 ───────────────────────────────────────────────
  {
    key: 'openai',
    name: 'OpenAI',
    group: '国际',
    base_url: 'https://api.openai.com/v1',
    docs_url: 'https://platform.openai.com/api-keys',
    key_hint: 'sk-...',
    models: [
      { key: 'gpt-4o', name: 'GPT-4o', capabilities: K(['text', 'code', 'vision']), context_window: 128000 },
      { key: 'gpt-4o-mini', name: 'GPT-4o mini', capabilities: K(['text', 'code', 'vision']), context_window: 128000 },
      { key: 'gpt-4-turbo', name: 'GPT-4 Turbo', capabilities: K(['text', 'code', 'vision']), context_window: 128000 },
      { key: 'o3-mini', name: 'o3-mini（推理）', capabilities: K(['text', 'code', 'reasoning']), context_window: 200000 },
      { key: 'o1', name: 'o1（推理）', capabilities: K(['text', 'code', 'reasoning']), context_window: 200000 },
    ],
  },
  {
    key: 'anthropic',
    name: 'Anthropic (Claude)',
    group: '国际',
    base_url: 'https://api.anthropic.com/v1',
    docs_url: 'https://console.anthropic.com/settings/keys',
    key_hint: 'sk-ant-...',
    models: [
      { key: 'claude-3-5-sonnet-latest', name: 'Claude 3.5 Sonnet', capabilities: K(['text', 'code', 'vision']), context_window: 200000 },
      { key: 'claude-3-5-haiku-latest', name: 'Claude 3.5 Haiku', capabilities: K(['text', 'code']), context_window: 200000 },
      { key: 'claude-3-opus-latest', name: 'Claude 3 Opus', capabilities: K(['text', 'code', 'vision']), context_window: 200000 },
      { key: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', capabilities: K(['text', 'code', 'vision']), context_window: 200000 },
    ],
  },
  {
    key: 'deepseek',
    name: 'DeepSeek',
    group: '国际',
    base_url: 'https://api.deepseek.com/v1',
    docs_url: 'https://platform.deepseek.com/api_keys',
    key_hint: 'sk-...',
    models: [
      { key: 'deepseek-chat', name: 'DeepSeek-V3 (Chat)', capabilities: K(['text', 'code']), context_window: 64000 },
      { key: 'deepseek-reasoner', name: 'DeepSeek-R1 (推理)', capabilities: K(['text', 'code', 'reasoning']), context_window: 64000 },
    ],
  },
  {
    key: 'groq',
    name: 'Groq',
    group: '国际',
    base_url: 'https://api.groq.com/openai/v1',
    docs_url: 'https://console.groq.com/keys',
    key_hint: 'gsk_...',
    models: [
      { key: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B', capabilities: K(['text', 'code']), context_window: 128000 },
      { key: 'llama-3.1-8b-instant', name: 'Llama 3.1 8B', capabilities: K(['text', 'code']), context_window: 128000 },
    ],
  },
  {
    key: 'openrouter',
    name: 'OpenRouter',
    group: '国际',
    base_url: 'https://openrouter.ai/api/v1',
    docs_url: 'https://openrouter.ai/keys',
    key_hint: 'sk-or-...',
    models: [
      { key: 'openai/gpt-4o', name: 'OpenAI: GPT-4o', capabilities: K(['text', 'code', 'vision']), context_window: 128000 },
      { key: 'anthropic/claude-3.5-sonnet', name: 'Anthropic: Claude 3.5 Sonnet', capabilities: K(['text', 'code', 'vision']), context_window: 200000 },
      { key: 'google/gemini-2.0-pro-exp-02-05', name: 'Google: Gemini 2.0 Pro', capabilities: K(['text', 'code', 'vision']), context_window: 2000000 },
      { key: 'meta-llama/llama-3.3-70b-instruct', name: 'Meta: Llama 3.3 70B', capabilities: K(['text', 'code']), context_window: 128000 },
    ],
  },
  {
    key: 'gemini',
    name: 'Google Gemini',
    group: '国际',
    base_url: 'https://generativelanguage.googleapis.com/v1beta/openai',
    docs_url: 'https://aistudio.google.com/app/apikey',
    key_hint: 'AIza...',
    models: [
      { key: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', capabilities: K(['text', 'code', 'vision']), context_window: 1000000 },
      { key: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', capabilities: K(['text', 'code', 'vision']), context_window: 1000000 },
    ],
  },
  {
    key: 'azure',
    name: 'Azure OpenAI',
    group: '国际',
    base_url: 'https://<your-resource>.openai.azure.com/openai',
    key_hint: '部署名即模型 key，如 gpt-4o',
    models: [
      { key: 'gpt-4o', name: 'gpt-4o（部署名）', capabilities: K(['text', 'code', 'vision']), context_window: 128000 },
      { key: 'gpt-4o-mini', name: 'gpt-4o-mini（部署名）', capabilities: K(['text', 'code', 'vision']), context_window: 128000 },
    ],
  },

  // ── 国内 ───────────────────────────────────────────────
  {
    key: 'qwen',
    name: '通义千问 (阿里云)',
    group: '国内',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    docs_url: 'https://help.aliyun.com/zh/model-studio/ManageAPIKey',
    key_hint: 'sk-...',
    models: [
      { key: 'qwen-max', name: 'Qwen-Max', capabilities: K(['text', 'code']), context_window: 32768 },
      { key: 'qwen-plus', name: 'Qwen-Plus', capabilities: K(['text', 'code']), context_window: 131072 },
      { key: 'qwen-turbo', name: 'Qwen-Turbo', capabilities: K(['text', 'code']), context_window: 131072 },
      { key: 'qwen2.5-72b-instruct', name: 'Qwen2.5-72B', capabilities: K(['text', 'code']), context_window: 131072 },
      { key: 'qwen-vl-max', name: 'Qwen-VL-Max（视觉）', capabilities: K(['text', 'vision']), context_window: 32768 },
    ],
  },
  {
    key: 'zhipu',
    name: '智谱 GLM (BigModel)',
    group: '国内',
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    docs_url: 'https://open.bigmodel.cn/usercenter/apikeys',
    key_hint: '...',
    models: [
      { key: 'glm-4-plus', name: 'GLM-4-Plus', capabilities: K(['text', 'code']), context_window: 128000 },
      { key: 'glm-4-air', name: 'GLM-4-Air', capabilities: K(['text', 'code']), context_window: 128000 },
      { key: 'glm-4-flash', name: 'GLM-4-Flash', capabilities: K(['text', 'code']), context_window: 128000 },
      { key: 'glm-4v-plus', name: 'GLM-4V-Plus（视觉）', capabilities: K(['text', 'vision']), context_window: 128000 },
    ],
  },
  {
    key: 'moonshot',
    name: 'Moonshot (Kimi)',
    group: '国内',
    base_url: 'https://api.moonshot.cn/v1',
    docs_url: 'https://platform.moonshot.cn/',
    key_hint: 'sk-...',
    models: [
      { key: 'moonshot-v1-8k', name: 'Kimi 8K', capabilities: K(['text', 'code']), context_window: 8192 },
      { key: 'moonshot-v1-32k', name: 'Kimi 32K', capabilities: K(['text', 'code']), context_window: 32768 },
      { key: 'moonshot-v1-128k', name: 'Kimi 128K', capabilities: K(['text', 'code']), context_window: 131072 },
    ],
  },
  {
    key: 'siliconflow',
    name: '硅基流动 (SiliconFlow)',
    group: '国内',
    base_url: 'https://api.siliconflow.cn/v1',
    docs_url: 'https://cloud.siliconflow.cn/account/ak',
    key_hint: 'sk-...',
    models: [
      { key: 'deepseek-ai/DeepSeek-V3', name: 'DeepSeek-V3', capabilities: K(['text', 'code']), context_window: 64000 },
      { key: 'Qwen/Qwen2.5-72B-Instruct', name: 'Qwen2.5-72B', capabilities: K(['text', 'code']), context_window: 32000 },
      { key: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen2.5-7B', capabilities: K(['text', 'code']), context_window: 32000 },
    ],
  },
  {
    key: 'volcengine',
    name: '火山方舟 (火山引擎)',
    group: '国内',
    base_url: 'https://ark.cn-beijing.volces.com/api/v3',
    docs_url: 'https://console.volcengine.com/ark',
    key_hint: 'API Key 在方舟控制台获取',
    models: [
      { key: 'doubao-pro-32k', name: 'Doubao-Pro-32K', capabilities: K(['text', 'code']), context_window: 32000 },
      { key: 'doubao-pro-256k', name: 'Doubao-Pro-256K', capabilities: K(['text', 'code']), context_window: 256000 },
    ],
  },

  // ── 本地 / 自建 ───────────────────────────────────────
  {
    key: 'ollama',
    name: 'Ollama（本地）',
    group: '本地 / 自建',
    base_url: 'http://localhost:11434/v1',
    docs_url: 'https://ollama.com/library',
    key_hint: '本地一般无需 Key，可留空',
    models: [
      { key: 'llama3.1', name: 'Llama 3.1', capabilities: K(['text', 'code']), context_window: 128000 },
      { key: 'qwen2.5', name: 'Qwen2.5', capabilities: K(['text', 'code']), context_window: 32000 },
      { key: 'mistral-nemo', name: 'Mistral Nemo', capabilities: K(['text', 'code']), context_window: 128000 },
    ],
  },
  {
    key: 'vllm',
    name: 'vLLM / 自建 OpenAI 兼容',
    group: '本地 / 自建',
    base_url: 'http://localhost:8000/v1',
    key_hint: '指向你的推理服务地址',
    models: [
      { key: 'local-model', name: '本地部署模型', capabilities: K(['text', 'code']), context_window: 32000 },
    ],
  },
]

/** 按 key 取预设 */
export function getPreset(key: string): ProviderPreset | undefined {
  return PROVIDER_PRESETS.find((p) => p.key === key)
}

/** 能力中文标签 */
export const CAPABILITY_LABELS: Record<ModelCapability, string> = {
  text: '文本',
  code: '代码',
  vision: '视觉',
  image: '图像',
  reasoning: '推理',
  audio: '语音',
}
