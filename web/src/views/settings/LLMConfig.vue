<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { LLMConfig } from '@/api/modules/llm'
import { llmApi } from '@/api/modules/llm'

const loading = ref(false)
const saving = ref(false)
const config = ref<LLMConfig | null>(null)

// Form state
const defaultModel = ref('')
const defaultTemperature = ref(0.7)
const maxTokens = ref(4096)
const apiKey = ref('')
const visionModel = ref('')
const imageGenModel = ref('')
const modelRoutesText = ref('{}')
const showApiKey = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await llmApi.get()
    config.value = res.data
    defaultModel.value = res.data.default_model
    defaultTemperature.value = res.data.default_temperature
    maxTokens.value = res.data.max_tokens
    modelRoutesText.value = JSON.stringify(res.data.model_routes, null, 2)
    // 不回填真实 key，只显示是否已设置
  } catch {
    ElMessage.error('获取 LLM 配置失败')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    let modelRoutes: Record<string, string> = {}
    try {
      modelRoutes = JSON.parse(modelRoutesText.value)
    } catch {
      ElMessage.error('Model Routes JSON 格式错误')
      saving.value = false
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
    ElMessage.success('配置已更新，部分设置需要重启服务后生效')
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

onMounted(load)
</script>

<template>
  <div class="llm-settings">
    <h2>LLM 配置</h2>

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
          已配置 API Key（点击眼睛图标显示/隐藏）
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
        <el-input v-model="visionModel" placeholder="qwen-vl-max（可选）" />
      </el-form-item>

      <el-form-item label="Image Gen 模型">
        <el-input v-model="imageGenModel" placeholder="wanx2.1-t2i-turbo（可选）" />
      </el-form-item>

      <el-form-item label="Model Routes">
        <el-input
          v-model="modelRoutesText"
          type="textarea"
          :rows="4"
          placeholder='{"claude": "anthropic/claude-3-5-sonnet"}'
        />
        <div class="hint">JSON 格式，key 为别名，value 为 LiteLLM 路由</div>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">
          保存配置
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped lang="scss">
.llm-settings {
  max-width: 720px;
}

.settings-form {
  margin-top: 16px;
}

.hint {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
