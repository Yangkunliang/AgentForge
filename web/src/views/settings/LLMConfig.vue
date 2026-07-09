<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { LLMConfig } from '@/api/modules/llm'
import { llmApi } from '@/api/modules/llm'

const loading = ref(false)
const saving = ref(false)
const creating = ref('')
const config = ref<LLMConfig | null>(null)

const defaultModel = ref('')
const defaultTemperature = ref(0.7)
const maxTokens = ref(4096)
const apiKey = ref('')
const visionModel = ref('')
const imageGenModel = ref('')
const modelRoutesText = ref('{}')
const showApiKey = ref(false)

const providerForm = reactive({
  provider_key: 'openai',
  name: 'OpenAI',
  base_url: '',
})

const modelForm = reactive({
  provider_id: '',
  model_key: '',
  name: '',
  capabilities: 'text,code',
  context_window: 128000,
})

const credentialForm = reactive({
  provider_id: '',
  name: '',
  secret: '',
})

const routeForm = reactive({
  route_key: 'default',
  name: '默认路由',
  provider_id: '',
  model_id: '',
  credential_id: '',
  temperature: 0.7,
  max_tokens: 4096,
  timeout_seconds: 60,
  fallback_route_keys: '',
})

const providers = computed(() => config.value?.providers ?? [])
const models = computed(() => config.value?.models ?? [])
const credentials = computed(() => config.value?.credentials ?? [])
const routes = computed(() => config.value?.routes ?? [])

const routeModels = computed(() =>
  models.value.filter((model) => model.provider_id === routeForm.provider_id),
)

const routeCredentials = computed(() =>
  credentials.value.filter((credential) => credential.provider_id === routeForm.provider_id),
)

async function load() {
  loading.value = true
  try {
    const res = await llmApi.get()
    config.value = res.data
    defaultModel.value = res.data.default_model
    defaultTemperature.value = res.data.default_temperature
    maxTokens.value = res.data.max_tokens
    modelRoutesText.value = JSON.stringify(res.data.model_routes, null, 2)
  } catch {
    ElMessage.error('获取 LLM 配置失败')
  } finally {
    loading.value = false
  }
}

async function saveLegacy() {
  saving.value = true
  try {
    let modelRoutes: Record<string, string> = {}
    try {
      modelRoutes = JSON.parse(modelRoutesText.value)
    } catch {
      ElMessage.error('Model Routes JSON 格式错误')
      return
    }

    await llmApi.update({
      default_model: defaultModel.value,
      default_temperature: defaultTemperature.value,
      max_tokens: maxTokens.value,
      model_routes: modelRoutes,
      api_key: apiKey.value || undefined,
      vision_model: visionModel.value || undefined,
      image_gen_model: imageGenModel.value || undefined,
    })
    ElMessage.success('配置已更新')
    apiKey.value = ''
    visionModel.value = ''
    imageGenModel.value = ''
    await load()
  } catch {
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

async function createProvider() {
  creating.value = 'provider'
  try {
    await llmApi.createProvider({
      provider_key: providerForm.provider_key,
      name: providerForm.name,
      base_url: providerForm.base_url || undefined,
      status: 'active',
    })
    ElMessage.success('Provider 已创建')
    await load()
  } catch {
    ElMessage.error('创建 Provider 失败')
  } finally {
    creating.value = ''
  }
}

async function createModel() {
  creating.value = 'model'
  try {
    await llmApi.createModel({
      provider_id: modelForm.provider_id,
      model_key: modelForm.model_key,
      name: modelForm.name,
      capabilities: splitCsv(modelForm.capabilities),
      context_window: modelForm.context_window || undefined,
      status: 'active',
    })
    ElMessage.success('Model 已创建')
    modelForm.model_key = ''
    modelForm.name = ''
    await load()
  } catch {
    ElMessage.error('创建 Model 失败')
  } finally {
    creating.value = ''
  }
}

async function createCredential() {
  creating.value = 'credential'
  try {
    await llmApi.createCredential({
      provider_id: credentialForm.provider_id,
      name: credentialForm.name,
      secret: credentialForm.secret,
      active: true,
    })
    ElMessage.success('Credential 已创建')
    credentialForm.name = ''
    credentialForm.secret = ''
    await load()
  } catch {
    ElMessage.error('创建 Credential 失败')
  } finally {
    creating.value = ''
  }
}

async function createRoute() {
  creating.value = 'route'
  try {
    await llmApi.createRoute({
      route_key: routeForm.route_key,
      name: routeForm.name,
      provider_id: routeForm.provider_id,
      model_id: routeForm.model_id,
      credential_id: routeForm.credential_id || null,
      temperature: routeForm.temperature,
      max_tokens: routeForm.max_tokens,
      timeout_seconds: routeForm.timeout_seconds,
      fallback_route_keys: splitCsv(routeForm.fallback_route_keys),
      active: true,
    })
    ElMessage.success('Route 已创建')
    await load()
  } catch {
    ElMessage.error('创建 Route 失败')
  } finally {
    creating.value = ''
  }
}

function splitCsv(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function onRouteProviderChange() {
  routeForm.model_id = ''
  routeForm.credential_id = ''
}

onMounted(load)
</script>

<template>
  <div class="llm-settings">
    <h2>LLM 配置</h2>

    <div v-loading="loading" class="settings-grid">
      <el-card shadow="never">
        <template #header>Provider</template>
        <el-form label-width="110px">
          <el-form-item label="Key">
            <el-input v-model="providerForm.provider_key" placeholder="openai" />
          </el-form-item>
          <el-form-item label="名称">
            <el-input v-model="providerForm.name" placeholder="OpenAI" />
          </el-form-item>
          <el-form-item label="Base URL">
            <el-input v-model="providerForm.base_url" placeholder="https://api.openai.com/v1" clearable />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="creating === 'provider'" @click="createProvider">
              新增 Provider
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>Model</template>
        <el-form label-width="110px">
          <el-form-item label="Provider">
            <el-select v-model="modelForm.provider_id" placeholder="选择 Provider" filterable>
              <el-option
                v-for="provider in providers"
                :key="provider.id"
                :label="provider.name"
                :value="provider.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Model Key">
            <el-input v-model="modelForm.model_key" placeholder="openai/gpt-4o-mini" />
          </el-form-item>
          <el-form-item label="名称">
            <el-input v-model="modelForm.name" placeholder="GPT-4o Mini" />
          </el-form-item>
          <el-form-item label="能力">
            <el-input v-model="modelForm.capabilities" placeholder="text,code,vision" />
          </el-form-item>
          <el-form-item label="上下文">
            <el-input-number v-model="modelForm.context_window" :min="1" :step="8192" />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :disabled="!modelForm.provider_id"
              :loading="creating === 'model'"
              @click="createModel"
            >
              新增 Model
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>Credential</template>
        <el-form label-width="110px">
          <el-form-item label="Provider">
            <el-select v-model="credentialForm.provider_id" placeholder="选择 Provider" filterable>
              <el-option
                v-for="provider in providers"
                :key="provider.id"
                :label="provider.name"
                :value="provider.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="名称">
            <el-input v-model="credentialForm.name" placeholder="prod-key" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="credentialForm.secret" type="password" placeholder="sk-..." show-password clearable />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :disabled="!credentialForm.provider_id"
              :loading="creating === 'credential'"
              @click="createCredential"
            >
              新增 Credential
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>Route</template>
        <el-form label-width="110px">
          <el-form-item label="Route Key">
            <el-input v-model="routeForm.route_key" placeholder="default" />
          </el-form-item>
          <el-form-item label="名称">
            <el-input v-model="routeForm.name" placeholder="默认路由" />
          </el-form-item>
          <el-form-item label="Provider">
            <el-select
              v-model="routeForm.provider_id"
              placeholder="选择 Provider"
              filterable
              @change="onRouteProviderChange"
            >
              <el-option
                v-for="provider in providers"
                :key="provider.id"
                :label="provider.name"
                :value="provider.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Model">
            <el-select v-model="routeForm.model_id" placeholder="选择 Model" filterable>
              <el-option
                v-for="model in routeModels"
                :key="model.id"
                :label="model.name"
                :value="model.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Credential">
            <el-select v-model="routeForm.credential_id" placeholder="可选" clearable filterable>
              <el-option
                v-for="credential in routeCredentials"
                :key="credential.id"
                :label="`${credential.name} (${credential.masked_secret})`"
                :value="credential.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Temperature">
            <el-input-number v-model="routeForm.temperature" :min="0" :max="2" :step="0.1" />
          </el-form-item>
          <el-form-item label="Max Tokens">
            <el-input-number v-model="routeForm.max_tokens" :min="1" :step="512" />
          </el-form-item>
          <el-form-item label="Timeout">
            <el-input-number v-model="routeForm.timeout_seconds" :min="1" :max="600" />
          </el-form-item>
          <el-form-item label="Fallback">
            <el-input v-model="routeForm.fallback_route_keys" placeholder="safe,cheap" clearable />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :disabled="!routeForm.provider_id || !routeForm.model_id"
              :loading="creating === 'route'"
              @click="createRoute"
            >
              新增 Route
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <el-card class="list-panel" shadow="never">
      <template #header>已配置 Route</template>
      <el-table :data="routes" size="small" empty-text="No Data">
        <el-table-column prop="route_key" label="Key" width="140" />
        <el-table-column prop="name" label="名称" width="160" />
        <el-table-column prop="provider_key" label="Provider" width="140" />
        <el-table-column prop="model_name" label="Model" min-width="220" />
        <el-table-column prop="credential_name" label="Credential" width="160" />
        <el-table-column prop="active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.active ? 'success' : 'info'" size="small">
              {{ row.active ? 'active' : 'inactive' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="legacy-panel" shadow="never">
      <template #header>兼容配置</template>
      <el-form
        v-loading="loading"
        label-width="160px"
        class="settings-form"
      >
        <el-form-item label="API Key">
          <el-input
            v-model="apiKey"
            :type="showApiKey ? 'text' : 'password'"
            placeholder="输入新的 API Key（留空则不修改）"
            clearable
          >
            <template #suffix>
              <el-icon v-if="config?.api_key_set" style="cursor:pointer" @click="showApiKey = !showApiKey">
                <View v-if="!showApiKey" />
                <Hide v-else />
              </el-icon>
            </template>
          </el-input>
          <div v-if="config?.api_key_set" class="hint">
            已配置 API Key
          </div>
        </el-form-item>

        <el-form-item label="默认模型">
          <el-input v-model="defaultModel" placeholder="openai/gpt-4o-mini" />
        </el-form-item>

        <el-form-item label="Temperature">
          <el-input-number v-model="defaultTemperature" :min="0" :max="2" :step="0.1" />
        </el-form-item>

        <el-form-item label="Max Tokens">
          <el-input-number v-model="maxTokens" :min="1" :step="512" />
        </el-form-item>

        <el-form-item label="Vision 模型">
          <el-input v-model="visionModel" placeholder="qwen-vl-max" />
        </el-form-item>

        <el-form-item label="Image Gen 模型">
          <el-input v-model="imageGenModel" placeholder="wanx2.1-t2i-turbo" />
        </el-form-item>

        <el-form-item label="Model Routes">
          <el-input
            v-model="modelRoutesText"
            type="textarea"
            :rows="4"
            placeholder='{"claude": "anthropic/claude-3-5-sonnet"}'
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveLegacy">
            保存兼容配置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.llm-settings {
  max-width: 1180px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.list-panel,
.legacy-panel {
  margin-top: 16px;
}

.settings-form {
  margin-top: 16px;
}

.hint {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

:deep(.el-select) {
  width: 100%;
}

@media (max-width: 900px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
