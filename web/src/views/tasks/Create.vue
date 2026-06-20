<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { tasksApi } from '@/api'
import type { CreateTaskForm } from '@/types'

const router = useRouter()

const form = reactive<CreateTaskForm>({
  description: '',
  priority: 'medium',
  expected_models: [],
})

const loading = ref(false)

async function handleSubmit() {
  if (!form.description.trim()) {
    ElMessage.warning('请输入任务描述')
    return
  }

  loading.value = true
  try {
    const { data } = await tasksApi.create(form)
    ElMessage.success('任务创建成功')
    router.push(`/tasks/${data.task_id}`)
  } catch {
    // 错误已在 request 中处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="task-create">
    <h1 class="page-title">创建任务</h1>

    <div class="card">
      <el-form :model="form" label-width="100px" class="create-form">
        <el-form-item label="任务描述" required>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="6"
            placeholder="请描述您的任务需求..."
          />
        </el-form-item>

        <el-form-item label="优先级">
          <el-radio-group v-model="form.priority">
            <el-radio label="low">低</el-radio>
            <el-radio label="medium">中</el-radio>
            <el-radio label="high">高</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="预期模型">
          <el-select v-model="form.expected_models" multiple placeholder="可选" clearable>
            <el-option label="gpt-4" value="gpt-4" />
            <el-option label="gpt-3.5-turbo" value="gpt-3.5-turbo" />
            <el-option label="claude-3-opus" value="claude-3-opus" />
            <el-option label="claude-3-sonnet" value="claude-3-sonnet" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button @click="router.back()">取消</el-button>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            创建任务
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
