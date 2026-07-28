<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '@/stores/agent'
import { agentsApi } from '@/api/modules/agents'
import type { AgentExpertise, CreateAgentForm } from '@/types'
import ExpertiseForm from './components/ExpertiseForm.vue'

const route = useRoute()
const router = useRouter()
const agentStore = useAgentStore()

const agentId = route.params.id as string
const loading = ref(false)
const saving = ref(false)
const loaded = ref(false)

// 注入预览相关状态
const previewVisible = ref(false)
const previewing = ref(false)
const previewText = ref('')
const previewEmpty = ref(false)

const form = reactive({
  name: '',
  capabilities: [] as string[],
  model: 'gpt-4',
  description: '',
  status: 'active' as 'active' | 'inactive',
  expertise: {} as AgentExpertise,
})

const capabilityOptions = [
  'code_generation',
  'code_review',
  'testing',
  'documentation',
  'refactoring',
  'research',
  'data_analysis',
]

onMounted(async () => {
  loading.value = true
  try {
    const agent = await agentStore.fetchAgent(agentId)
    form.name = agent.name
    form.capabilities = agent.capabilities || []
    form.model = agent.model
    form.description = agent.description || ''
    form.status = agent.status
    form.expertise = agent.expertise ? { ...agent.expertise } : {}
    loaded.value = true
  } catch {
    // request 已处理
  } finally {
    loading.value = false
  }
})

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入 Agent 名称')
    return
  }
  saving.value = true
  try {
    const payload: Partial<CreateAgentForm> = {
      name: form.name,
      capabilities: form.capabilities,
      model: form.model,
      description: form.description,
      status: form.status,
      expertise: form.expertise,
    }
    await agentStore.updateAgent(agentId, payload)
    ElMessage.success('保存成功')
    router.push('/agents')
  } catch {
    // request 已处理
  } finally {
    saving.value = false
  }
}

async function onPreview() {
  previewing.value = true
  try {
    const res = await agentsApi.previewExpertise(agentId, form.expertise)
    previewEmpty.value = res.data.is_empty
    previewText.value = res.data.prompt_section
    previewVisible.value = true
  } catch {
    // request 已处理
  } finally {
    previewing.value = false
  }
}
</script>

<template>
  <div class="agent-edit">
    <h1 class="page-title">编辑 Agent</h1>

    <div v-loading="loading" class="cards">
      <div class="card">
        <h2 class="card-title">基本信息</h2>
        <el-form :model="form" label-width="100px" class="edit-form">
          <el-form-item label="名称" required>
            <el-input v-model="form.name" placeholder="Agent 名称" />
          </el-form-item>

          <el-form-item label="能力">
            <el-checkbox-group v-model="form.capabilities">
              <el-checkbox v-for="cap in capabilityOptions" :key="cap" :label="cap">
                {{ cap }}
              </el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-form-item label="模型">
            <el-select v-model="form.model">
              <el-option label="GPT-4" value="gpt-4" />
              <el-option label="GPT-3.5 Turbo" value="gpt-3.5-turbo" />
              <el-option label="Claude 3 Opus" value="claude-3-opus" />
              <el-option label="Claude 3 Sonnet" value="claude-3-sonnet" />
            </el-select>
          </el-form-item>

          <el-form-item label="状态">
            <el-radio-group v-model="form.status">
              <el-radio label="active">启用</el-radio>
              <el-radio label="inactive">停用</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>
      </div>

      <div class="card">
        <div class="card-head">
          <h2 class="card-title">专家模型</h2>
          <el-button size="small" :loading="previewing" @click="onPreview">
            👁 预览注入内容
          </el-button>
        </div>
        <ExpertiseForm v-if="loaded" v-model="form.expertise" />
        <div v-else class="ef-placeholder">加载中…</div>
      </div>

      <div class="actions">
        <el-button @click="router.back()">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </div>
    </div>

    <el-dialog v-model="previewVisible" title="注入到 System Prompt 的内容" width="720px">
      <el-alert
        v-if="previewEmpty"
        type="warning"
        :closable="false"
        title="该 Agent 暂未配置专家模型"
        description="保存后不会向 System Prompt 注入额外工程标准。"
      />
      <pre v-else class="preview-block">{{ previewText }}</pre>
      <p class="preview-tip">
        以上即为 Agent 在每个阶段执行时，注入到 system prompt 可信区的「专家工作标准」原文；它与运行时实际注入内容完全一致（同一渲染函数，零漂移）。
      </p>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.edit-form {
  max-width: 600px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 16px;
  color: var(--el-text-color-primary, #303133);
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  .card-title {
    margin: 0;
  }
}
.preview-block {
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--el-fill-color-light, #f5f7fa);
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: 6px;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-primary, #303133);
  margin: 0;
  max-height: 60vh;
  overflow: auto;
  font-family: var(--el-font-family, inherit);
}
.preview-tip {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
  line-height: 1.6;
}
.cards {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.ef-placeholder {
  color: var(--el-text-color-secondary, #909399);
}
</style>
