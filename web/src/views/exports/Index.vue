<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { exportsApi } from '@/api'
import type { ExportTask, CreateExportForm } from '@/types'

const exportTasks = ref<ExportTask[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)

const createForm = ref<CreateExportForm>({
  type: 'training_data',
  start_date: '',
  end_date: '',
  format: 'jsonl',
  delevel: 'level_1',
})

async function fetchExports() {
  loading.value = true
  try {
    const { data } = await exportsApi.list()
    exportTasks.value = data.items
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  try {
    const { data } = await exportsApi.create(createForm.value)
    ElMessage.success('导出任务已创建')
    showCreateDialog.value = false
    fetchExports()
    pollStatus(data.export_id)
  } catch {
    // 错误已在 request 中处理
  }
}

async function pollStatus(exportId: string) {
  const interval = setInterval(async () => {
    const { data } = await exportsApi.getStatus(exportId)
    const task = exportTasks.value.find((t) => t.export_id === exportId)
    if (task) {
      task.status = data.status
      task.total_records = data.total_records
      task.file_path = data.file_path
    }

    if (data.status !== 'processing') {
      clearInterval(interval)
      if (data.status === 'done') {
        ElMessage.success('导出完成，可以下载了')
      } else {
        ElMessage.error('导出失败')
      }
    }
  }, 3000)
}

function downloadFile(exportId: string) {
  window.open(exportsApi.download(exportId), '_blank')
}

function getStatusTagType(status: string): string {
  const map: Record<string, string> = {
    processing: 'primary',
    done: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

onMounted(fetchExports)
</script>

<template>
  <div class="export-list">
    <div class="page-header">
      <h1 class="page-title">数据导出</h1>
      <el-button type="primary" @click="showCreateDialog = true">新建导出</el-button>
    </div>

    <div class="card">
      <el-table :data="exportTasks" v-loading="loading">
        <el-table-column prop="export_id" label="ID" width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_records" label="记录数" width="100" />
        <el-table-column prop="estimated_size_mb" label="预计大小(MB)" width="140">
          <template #default="{ row }">
            {{ row.estimated_size_mb.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'done' && row.file_path"
              type="primary"
              link
              size="small"
              @click="downloadFile(row.export_id)"
            >
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showCreateDialog" title="新建导出任务" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="导出类型">
          <el-select v-model="createForm.type">
            <el-option label="训练数据" value="training_data" />
            <el-option label="API 日志" value="api_logs" />
            <el-option label="任务记录" value="task_records" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="createForm.start_date" type="date" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="createForm.end_date" type="date" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="脱敏级别">
          <el-select v-model="createForm.delevel">
            <el-option label="Level 1 (轻度)" value="level_1" />
            <el-option label="Level 2 (中度)" value="level_2" />
            <el-option label="Level 3 (重度)" value="level_3" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
}
</style>
