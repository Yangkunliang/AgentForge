<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'

const router = useRouter()
const taskStore = useTaskStore()

const filterForm = reactive({
  status: '',
  priority: '',
})

onMounted(() => {
  taskStore.fetchTasks()
})

function handleFilter() {
  taskStore.fetchTasks({
    status: filterForm.status || undefined,
    priority: filterForm.priority || undefined,
  })
}

function getStatusTagType(status: string): string {
  const map: Record<string, string> = {
    pending: 'warning',
    processing: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

function getPriorityTagType(priority: string): string {
  const map: Record<string, string> = {
    low: 'info',
    medium: 'warning',
    high: 'danger',
  }
  return map[priority] || 'info'
}

function goToCreate() {
  router.push('/tasks/create')
}

function goToDetail(taskId: string) {
  router.push(`/tasks/${taskId}`)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}
</script>

<template>
  <div class="task-list">
    <div class="page-header">
      <h1 class="page-title">任务列表</h1>
      <el-button type="primary" @click="goToCreate">创建任务</el-button>
    </div>

    <div class="card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="待处理" value="pending" />
            <el-option label="进行中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="filterForm.priority" @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-table :data="taskStore.tasks" v-loading="taskStore.loading" @row-click="goToDetail">
        <el-table-column prop="task_id" label="ID" width="180" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="getPriorityTagType(row.priority)" size="small">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_cost_usd" label="费用" width="100">
          <template #default="{ row }">
            ${{ (row.total_cost_usd ?? 0).toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="taskStore.pagination.page"
        :total="taskStore.pagination.total"
        :page-size="taskStore.pagination.per_page"
        layout="total, prev, pager, next"
        class="pagination"
        @current-change="handleFilter"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
}

.filter-form {
  margin-bottom: $spacing-md;
}

.pagination {
  margin-top: $spacing-md;
  justify-content: flex-end;
}
</style>
