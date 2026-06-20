<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '@/stores/agent'
import type { CreateAgentForm } from '@/types'

const router = useRouter()
const agentStore = useAgentStore()

const form = reactive<CreateAgentForm>({
  name: '',
  capabilities: [],
  model: 'gpt-4',
  description: '',
})

const loading = ref(false)

const capabilityOptions = [
  'code_generation',
  'code_review',
  'testing',
  'documentation',
  'refactoring',
  'research',
  'data_analysis',
]

async function handleSubmit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入 Agent 名称')
    return
  }
  if (form.capabilities.length === 0) {
    ElMessage.warning('请选择至少一个能力')
    return
  }

  loading.value = true
  try {
    await agentStore.createAgent(form)
    ElMessage.success('Agent 创建成功')
    router.push('/agents')
  } catch {
    // 错误已在 request 中处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="agent-create">
    <h1 class="page-title">创建 Agent</h1>

    <div class="card">
      <el-form :model="form" label-width="100px" class="create-form">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="Agent 名称" />
        </el-form-item>

        <el-form-item label="能力" required>
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

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>

        <el-form-item>
          <el-button @click="router.back()">取消</el-button>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            创建
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped lang="scss">
.create-form {
  max-width: 600px;
}
</style>
