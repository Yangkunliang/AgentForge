<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { LLMConfig, LLMModel, LLMRoute } from '@/api/modules/llm'
import { llmApi } from '@/api/modules/llm'
import {
  CAPABILITY_LABELS,
  getPreset,
  PROVIDER_PRESETS,
  type ModelCapability,
  type ProviderPreset,
} from '@/data/llmProviderPresets'

const loading = ref(false)
const saving = ref(false)

const config = ref<LLMConfig | null>(null)

// ── 默认参数 ──────────────────────────────────────────────
const defaultModel = ref('')
const defaultTemperature = ref(0.7)
const maxTokens = ref(4096)
const visionModel = ref('')
const imageGenModel = ref('')
const globalApiKey = ref('')
const showGlobalApiKey = ref(false)
const modelRoutesRows = ref<Array<{ key: string; target: string }>>([])

// ── 已配置数据 ────────────────────────────────────────────
const providers = computed(() => config.value?.providers ?? [])
const models = computed(() => config.value?.models ?? [])
const credentials = computed(() => config.value?.credentials ?? [])
const routes = computed(() => config.value?.routes ?? [])

// ── 引导式快速配置 ────────────────────────────────────────
const presetKey = ref('')
const draftProvider = reactive({ name: '', base_url: '' })
const setupProviderId = ref('')
const credentialName = ref('默认密钥')
const credentialSecret = ref('')
const showCredentialSecret = ref(false)
const selectedModelKeys = ref<string[]>([])

const setupProvider = computed(() => providers.value.find((p) => p.id === setupProviderId.value) ?? null)
const setupPreset = computed<ProviderPreset | undefined>(() =>
  setupProvider.value ? getPreset(setupProvider.value.provider_key) : undefined,
)
const setupPresetModels = computed(() => setupPreset.value?.models ?? [])
const existingModelKeys = computed(() => {
  const set = new Set<string>()
  for (const m of models.value) if (m.provider_id === setupProviderId.value) set.add(m.model_key)
  return set
})
// 待添加（未被勾选移除、且尚未存在）的推荐模型
const pendingModels = computed(() =>
  setupPresetModels.value.filter(
    (m) => selectedModelKeys.value.includes(m.key) && !existingModelKeys.value.has(m.key),
  ),
)

const addedProviderExists = computed(() => !!setupProvider.value)

function onPresetChange(key: string) {
  const preset = getPreset(key)
  if (preset) {
    draftProvider.name = preset.name
    draftProvider.base_url = preset.base_url
  } else {
    draftProvider.name = ''
    draftProvider.base_url = ''
  }
}

async function addProvider() {
  if (!presetKey.value) {
    ElMessage.warning('请先选择一个服务商')
    return
  }
  const preset = getPreset(presetKey.value)!
  try {
    const { data } = await llmApi.createProvider({
      provider_key: preset.key,
      name: draftProvider.name || preset.name,
      base_url: draftProvider.base_url || undefined,
      status: 'active',
    })
    setupProviderId.value = data.id
    selectedModelKeys.value = preset.models.map((m) => m.key)
    ElMessage.success(`已添加服务商「${data.name}」，继续配置密钥与模型`)
    await load()
  } catch {
    ElMessage.error('添加服务商失败（可能已存在同名服务商）')
  }
}

async function addCredential() {
  if (!setupProviderId.value) {
    ElMessage.warning('请先添加或选择一个服务商')
    return
  }
  if (!credentialSecret.value.trim()) {
    ElMessage.warning('请输入 API Key')
    return
  }
  try {
    await llmApi.createCredential({
      provider_id: setupProviderId.value,
      name: credentialName.value || '默认密钥',
      secret: credentialSecret.value.trim(),
      active: true,
    })
    credentialSecret.value = ''
    ElMessage.success('密钥已保存')
    await load()
  } catch {
    ElMessage.error('保存密钥失败')
  }
}

async function addSelectedModels() {
  if (!setupProviderId.value) {
    ElMessage.warning('请先添加或选择一个服务商')
    return
  }
  const toAdd = pendingModels.value
  if (toAdd.length === 0) {
    ElMessage.info('没有需要新增的模型（已全部添加或已取消勾选）')
    return
  }
  let ok = 0
  for (const m of toAdd) {
    try {
      await llmApi.createModel({
        provider_id: setupProviderId.value,
        model_key: m.key,
        name: m.name,
        capabilities: m.capabilities,
        context_window: m.context_window,
        status: 'active',
      })
      ok += 1
    } catch {
      /* 忽略单个失败，继续 */
    }
  }
  if (ok > 0) {
    ElMessage.success(`已添加 ${ok} 个模型`)
    await load()
  } else {
    ElMessage.error('模型添加失败')
  }
}

// ── 默认参数保存 ──────────────────────────────────────────
function rowsToRoutesDict(): Record<string, string> {
  const dict: Record<string, string> = {}
  for (const row of modelRoutesRows.value) {
    if (row.key.trim() && row.target.trim()) dict[row.key.trim()] = row.target.trim()
  }
  return dict
}

async function saveDefaults() {
  saving.value = true
  try {
    await llmApi.update({
      default_model: defaultModel.value,
      default_temperature: defaultTemperature.value,
      max_tokens: maxTokens.value,
      model_routes: rowsToRoutesDict(),
      api_key: globalApiKey.value || undefined,
      vision_model: visionModel.value || undefined,
      image_gen_model: imageGenModel.value || undefined,
    })
    ElMessage.success('默认参数已保存')
    globalApiKey.value = ''
    await load()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// ── 路由管理 ──────────────────────────────────────────────
const routeDialogVisible = ref(false)
const submittingRoute = ref(false)
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

const routeModels = computed(() => models.value.filter((m) => m.provider_id === routeForm.provider_id))
const routeCredentials = computed(() =>
  credentials.value.filter((c) => c.provider_id === routeForm.provider_id),
)

function openRouteDialog() {
  routeForm.route_key = `route-${routes.value.length + 1}`
  routeForm.name = '新路由'
  routeForm.provider_id = ''
  routeForm.model_id = ''
  routeForm.credential_id = ''
  routeForm.temperature = 0.7
  routeForm.max_tokens = 4096
  routeForm.timeout_seconds = 60
  routeForm.fallback_route_keys = ''
  routeDialogVisible.value = true
}

function onRouteProviderChange() {
  routeForm.model_id = ''
  routeForm.credential_id = ''
}

async function submitRoute() {
  if (!routeForm.provider_id || !routeForm.model_id) {
    ElMessage.warning('请选择 Provider 与 Model')
    return
  }
  submittingRoute.value = true
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
      fallback_route_keys: routeForm.fallback_route_keys
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      active: true,
    })
    ElMessage.success('路由已创建')
    routeDialogVisible.value = false
    await load()
  } catch {
    ElMessage.error('创建路由失败（route_key 可能已存在）')
  } finally {
    submittingRoute.value = false
  }
}

// ── 模型路由映射（结构化编辑，替代原始 JSON）─────────────
function addRouteRow() {
  modelRoutesRows.value.push({ key: '', target: '' })
}
function removeRouteRow(idx: number) {
  modelRoutesRows.value.splice(idx, 1)
}

// ── 选择器数据 ────────────────────────────────────────────
function modelsOfProvider(providerId: string): LLMModel[] {
  return models.value.filter((m) => m.provider_id === providerId)
}

const groupedModelOptions = computed(() =>
  providers.value.map((p) => ({ provider: p, items: modelsOfProvider(p.id) })),
)

const capabilityLabel = (c: string) => CAPABILITY_LABELS[c as ModelCapability] ?? c

const connectionReady = computed(
  () =>
    !!defaultModel.value &&
    routes.value.some((r: LLMRoute) => r.active) &&
    credentials.value.some((c) => c.active),
)

async function load() {
  loading.value = true
  try {
    const res = await llmApi.get()
    config.value = res.data
    defaultModel.value = res.data.default_model
    defaultTemperature.value = res.data.default_temperature
    maxTokens.value = res.data.max_tokens
    modelRoutesRows.value = Object.entries(res.data.model_routes ?? {}).map(([key, target]) => ({
      key,
      target,
    }))
  } catch {
    ElMessage.error('获取 LLM 配置失败')
  } finally {
    loading.value = false
  }
}

// 若已存在服务商，默认把第一个作为「引导配置」目标，便于继续补模型/密钥
watch(
  providers,
  (list) => {
    if (!setupProviderId.value && list.length > 0) {
      setupProviderId.value = list[0].id
      const preset = getPreset(list[0].provider_key)
      if (preset) selectedModelKeys.value = preset.models.map((m) => m.key)
    }
  },
  { immediate: true },
)

onMounted(load)
</script>

<template>
  <div class="llm-settings">
    <header class="page-head">
      <div>
        <h2>大模型配置</h2>
        <p class="page-sub">选择服务商并填入密钥即可开始，绝大多数选项已为你预置好默认值。</p>
      </div>
      <el-tag :type="connectionReady ? 'success' : 'info'" effect="light" round>
        {{ connectionReady ? '✓ 配置就绪' : '待完成配置' }}
      </el-tag>
    </header>

    <div v-loading="loading">
      <!-- 概览 -->
      <div class="stat-row">
        <div class="stat"><span class="stat__num">{{ providers.length }}</span><span class="stat__label">服务商</span></div>
        <div class="stat"><span class="stat__num">{{ models.length }}</span><span class="stat__label">模型</span></div>
        <div class="stat"><span class="stat__num">{{ credentials.length }}</span><span class="stat__label">密钥</span></div>
        <div class="stat"><span class="stat__num">{{ routes.length }}</span><span class="stat__label">路由</span></div>
      </div>

      <!-- 引导式快速配置 -->
      <h3 class="section-title">快速配置</h3>
      <div class="setup-grid">
        <!-- Step 1 -->
        <el-card shadow="never" class="setup-card">
          <div class="step-badge">1</div>
          <div class="setup-card__title">选择服务商</div>
          <p class="setup-card__hint">点选即可自动带出 Base URL，无需手填。</p>
          <el-select
            v-model="presetKey"
            placeholder="搜索服务商…"
            filterable
            class="block"
            @change="onPresetChange"
          >
            <el-option-group v-for="group in ['国际', '国内', '本地 / 自建']" :key="group" :label="group">
              <el-option
                v-for="p in PROVIDER_PRESETS.filter((x) => x.group === group)"
                :key="p.key"
                :label="p.name"
                :value="p.key"
              />
            </el-option-group>
          </el-select>
          <template v-if="presetKey">
            <el-input v-model="draftProvider.name" placeholder="服务商名称" class="mt8" />
            <el-input v-model="draftProvider.base_url" placeholder="Base URL" class="mt8">
              <template v-if="getPreset(presetKey)?.docs_url" #append>
                <a :href="getPreset(presetKey)!.docs_url" target="_blank" rel="noopener" class="doc-link">申请 Key</a>
              </template>
            </el-input>
            <el-button type="primary" class="mt8 block" :disabled="addedProviderExists" @click="addProvider">
              {{ addedProviderExists ? '已添加，可继续下方步骤' : '添加服务商' }}
            </el-button>
          </template>
        </el-card>

        <!-- Step 2 -->
        <el-card shadow="never" class="setup-card">
          <div class="step-badge">2</div>
          <div class="setup-card__title">配置 API Key</div>
          <p class="setup-card__hint">密钥仅加密存储，页面不展示明文。</p>
          <el-select v-model="setupProviderId" placeholder="选择服务商" filterable class="block">
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-input v-model="credentialName" placeholder="密钥名称" class="mt8" />
          <el-input
            v-model="credentialSecret"
            :type="showCredentialSecret ? 'text' : 'password'"
            :placeholder="setupPreset?.key_hint || 'sk-...'"
            show-password
            class="mt8"
          />
          <el-button
            type="primary"
            class="mt8 block"
            :disabled="!setupProviderId || !credentialSecret.trim()"
            @click="addCredential"
          >
            保存密钥
          </el-button>
        </el-card>

        <!-- Step 3 -->
        <el-card shadow="never" class="setup-card">
          <div class="step-badge">3</div>
          <div class="setup-card__title">勾选模型</div>
          <p class="setup-card__hint">
            {{ setupPreset ? `来自「${setupPreset.name}」的推荐模型，勾选后批量添加：` : '该服务商暂无推荐清单，可到下方手动添加。' }}
          </p>
          <el-checkbox-group v-if="setupPresetModels.length" v-model="selectedModelKeys" class="model-check">
            <el-checkbox
              v-for="m in setupPresetModels"
              :key="m.key"
              :value="m.key"
              :disabled="existingModelKeys.has(m.key)"
            >
              <span class="model-check__name">{{ m.name }}</span>
              <span class="model-check__caps">
                <el-tag
                  v-for="c in m.capabilities"
                  :key="c"
                  size="small"
                  type="info"
                  effect="plain"
                  class="cap-tag"
                >{{ capabilityLabel(c) }}</el-tag>
                <el-tag v-if="existingModelKeys.has(m.key)" size="small" type="success" effect="plain">已添加</el-tag>
              </span>
            </el-checkbox>
          </el-checkbox-group>
          <el-button
            type="primary"
            class="mt8 block"
            :disabled="!setupProviderId || pendingModels.length === 0"
            @click="addSelectedModels"
          >
            添加选中模型（{{ pendingModels.length }}）
          </el-button>
        </el-card>
      </div>

      <!-- 默认参数 -->
      <h3 class="section-title">默认参数</h3>
      <el-card shadow="never" class="panel">
        <el-form label-width="140px" class="settings-form">
          <el-form-item label="默认模型">
            <el-select v-model="defaultModel" placeholder="选择默认模型" filterable class="block">
              <el-option-group v-for="g in groupedModelOptions" :key="g.provider.id" :label="g.provider.name">
                <el-option v-for="m in g.items" :key="m.id" :label="m.name" :value="m.model_key" />
              </el-option-group>
            </el-select>
          </el-form-item>
          <el-form-item label="Temperature">
            <el-slider v-model="defaultTemperature" :min="0" :max="2" :step="0.1" show-input class="block" />
          </el-form-item>
          <el-form-item label="Max Tokens">
            <el-input-number v-model="maxTokens" :min="1" :step="512" />
          </el-form-item>
          <el-form-item label="视觉模型">
            <el-select v-model="visionModel" placeholder="可选" filterable clearable class="block">
              <el-option-group v-for="g in groupedModelOptions" :key="g.provider.id" :label="g.provider.name">
                <el-option v-for="m in g.items" :key="m.id" :label="m.name" :value="m.model_key" />
              </el-option-group>
            </el-select>
          </el-form-item>
          <el-form-item label="图像生成模型">
            <el-input v-model="imageGenModel" placeholder="如 wanx2.1-t2i-turbo（可选）" clearable class="block" />
          </el-form-item>
          <el-form-item label="全局 API Key">
            <el-input
              v-model="globalApiKey"
              :type="showGlobalApiKey ? 'text' : 'password'"
              placeholder="留空则不修改；一般请在上一步按服务商配置密钥"
              show-password
              clearable
              class="block"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveDefaults">保存默认参数</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 高级：路由与映射 -->
      <el-collapse class="adv-collapse">
        <el-collapse-item title="高级设置 · 路由与模型映射" name="adv">
          <div class="adv-head">
            <span class="adv-head__title">已配置路由</span>
            <el-button size="small" type="primary" plain @click="openRouteDialog">新增路由</el-button>
          </div>
          <el-table :data="routes" size="small" empty-text="暂无路由" class="mb16">
            <el-table-column prop="name" label="名称" min-width="160" />
            <el-table-column prop="provider_key" label="Provider" width="150" />
            <el-table-column prop="model_name" label="Model" min-width="200" />
            <el-table-column prop="credential_name" label="Credential" width="150" />
            <el-table-column prop="active" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.active ? 'success' : 'info'" size="small">
                  {{ row.active ? 'active' : 'inactive' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <div class="adv-head">
            <span class="adv-head__title">模型路由映射</span>
            <el-button size="small" @click="addRouteRow">添加一行</el-button>
          </div>
          <p class="setup-card__hint">将模型别名映射到真实模型（如把 <code>claude</code> 指向 <code>anthropic/claude-3-5-sonnet</code>）。</p>
          <div v-for="(row, idx) in modelRoutesRows" :key="idx" class="route-row">
            <el-input v-model="row.key" placeholder="别名，如 claude" class="route-row__key" />
            <span class="route-row__arrow">→</span>
            <el-select v-model="row.target" placeholder="真实模型" filterable class="route-row__target">
              <el-option-group v-for="g in groupedModelOptions" :key="g.provider.id" :label="g.provider.name">
                <el-option v-for="m in g.items" :key="m.id" :label="m.name" :value="m.model_key" />
              </el-option-group>
            </el-select>
            <el-button text type="danger" :icon="'Delete'" @click="removeRouteRow(idx)" />
          </div>
          <div class="mt8">
            <el-button type="primary" :loading="saving" @click="saveDefaults">保存映射</el-button>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 新增路由弹窗 -->
    <el-dialog v-model="routeDialogVisible" title="新增路由" width="560px">
      <el-form label-width="120px">
        <el-form-item label="Route Key">
          <el-input v-model="routeForm.route_key" placeholder="default" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="routeForm.name" placeholder="默认路由" />
        </el-form-item>
        <el-form-item label="Provider">
          <el-select v-model="routeForm.provider_id" placeholder="选择 Provider" filterable class="block" @change="onRouteProviderChange">
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Model">
          <el-select v-model="routeForm.model_id" placeholder="选择 Model" filterable class="block">
            <el-option v-for="m in routeModels" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Credential">
          <el-select v-model="routeForm.credential_id" placeholder="可选" clearable filterable class="block">
            <el-option v-for="c in routeCredentials" :key="c.id" :label="`${c.name}`" :value="c.id" />
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
          <el-input v-model="routeForm.fallback_route_keys" placeholder="逗号分隔的备用路由 key" clearable class="block" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="routeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingRoute" @click="submitRoute">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.llm-settings {
  max-width: 1080px;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #1f2937;
  }
}

.page-sub {
  margin: 6px 0 0;
  font-size: 13px;
  color: #94a3b8;
}

.stat-row {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 10px;

  &__num {
    font-size: 22px;
    font-weight: 700;
    color: #1d4ed8;
  }

  &__label {
    font-size: 12px;
    color: #94a3b8;
  }
}

.section-title {
  margin: 24px 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: #334155;
}

.setup-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.setup-card {
  position: relative;
  padding-top: 12px !important;

  &__title {
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
    margin-top: 8px;
  }

  &__hint {
    font-size: 12px;
    color: #94a3b8;
    margin: 4px 0 12px;
    line-height: 1.5;
  }
}

.step-badge {
  position: absolute;
  top: 14px;
  right: 16px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #eef2ff;
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.model-check {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 220px;
  overflow-y: auto;
  width: 100%;

  :deep(.el-checkbox) {
    width: 100%;
    height: auto;
    margin-right: 0;
    padding: 4px 0;
    white-space: normal;
  }

  &__name {
    font-weight: 500;
    margin-right: 6px;
  }

  &__caps {
    display: inline-flex;
    gap: 4px;
    flex-wrap: wrap;
    vertical-align: middle;
  }
}

.cap-tag {
  height: 18px;
  padding: 0 5px;
  line-height: 16px;
}

.doc-link {
  font-size: 12px;
  color: #1d4ed8;
  text-decoration: none;
}

.panel,
.adv-collapse {
  margin-top: 4px;
}

.settings-form {
  margin-top: 4px;
}

.block {
  width: 100%;
}

.mt8 {
  margin-top: 8px;
}

.mb16 {
  margin-bottom: 16px;
}

.adv-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 8px 0;

  &__title {
    font-size: 14px;
    font-weight: 600;
    color: #334155;
  }
}

.route-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;

  &__key {
    flex: 0 0 200px;
  }

  &__arrow {
    color: #94a3b8;
  }

  &__target {
    flex: 1;
  }
}

:deep(.el-select) {
  width: 100%;
}

:deep(.el-slider) {
  width: 100%;
}

@media (max-width: 900px) {
  .setup-grid {
    grid-template-columns: 1fr;
  }
}
</style>
