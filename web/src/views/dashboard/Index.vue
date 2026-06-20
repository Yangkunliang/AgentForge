<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '@/api'
import type { DashboardStats } from '@/types'

const router = useRouter()
const stats = ref<DashboardStats | null>(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await dashboardApi.get()
    stats.value = data
  } finally {
    loading.value = false
  }
})

function getStatusClass(status: string): string {
  return `status-tag--${status}`
}

function formatCost(cost: number): string {
  return cost.toFixed(4)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

function goToTask(taskId: string) {
  router.push(`/tasks/${taskId}`)
}
</script>

<template>
  <div class="dashboard">
    <h1 class="page-title">Dashboard</h1>

    <div v-loading="loading">
      <!-- 任务统计卡片 -->
      <el-row :gutter="16" class="stats-row">
        <el-col :span="6">
          <div class="stat-card stat-card--pending">
            <div class="stat-value">{{ stats?.tasks.pending ?? 0 }}</div>
            <div class="stat-label">待处理</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-card--processing">
            <div class="stat-value">{{ stats?.tasks.processing ?? 0 }}</div>
            <div class="stat-label">进行中</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-card--completed">
            <div class="stat-value">{{ stats?.tasks.completed ?? 0 }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-card--failed">
            <div class="stat-value">{{ stats?.tasks.failed ?? 0 }}</div>
            <div class="stat-label">失败</div>
          </div>
        </el-col>
      </el-row>

      <!-- 费用统计 -->
      <el-row :gutter="16" class="stats-row">
        <el-col :span="12">
          <div class="card">
            <div class="card__header">今日费用</div>
            <div class="cost-display">
              <span class="cost-value">${{ formatCost(stats?.cost.today_usd ?? 0) }}</span>
              <span
                class="cost-trend"
                :class="{ 'cost-trend--up': (stats?.cost.trend_pct ?? 0) > 0 }"
              >
                {{ (stats?.cost.trend_pct ?? 0) > 0 ? '+' : '' }}{{ stats?.cost.trend_pct ?? 0 }}%
              </span>
            </div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="card">
            <div class="card__header">Agent & Skill</div>
            <div class="agent-skill-stats">
              <div class="as-item">
                <el-icon><User /></el-icon>
                <span>{{ stats?.agents.active ?? 0 }} 活跃</span>
              </div>
              <div class="as-item">
                <el-icon><Grid /></el-icon>
                <span>{{ stats?.skills.total ?? 0 }} Skill</span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 最近任务 -->
      <div class="card">
        <div class="card__header">最近任务</div>
        <el-table :data="stats?.recent_tasks" style="width: 100%">
          <el-table-column prop="task_id" label="ID" width="180" />
          <el-table-column prop="description" label="描述" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :class="getStatusClass(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="primary" link @click="goToTask(row.task_id)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stats-row {
  margin-bottom: $spacing-md;
}

.stat-card {
  background: #fff;
  border-radius: $border-radius-md;
  padding: $spacing-lg;
  text-align: center;

  .stat-value {
    font-size: 32px;
    font-weight: 600;
    margin-bottom: $spacing-sm;
  }

  .stat-label {
    font-size: 14px;
    color: #909399;
  }

  &--pending .stat-value {
    color: #e6a23c;
  }

  &--processing .stat-value {
    color: #409eff;
  }

  &--completed .stat-value {
    color: #67c23a;
  }

  &--failed .stat-value {
    color: #f56c6c;
  }
}

.cost-display {
  display: flex;
  align-items: baseline;
  gap: $spacing-md;
}

.cost-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.cost-trend {
  font-size: 14px;
  color: #67c23a;

  &--up {
    color: #f56c6c;
  }
}

.agent-skill-stats {
  display: flex;
  gap: $spacing-xl;
}

.as-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: 16px;
  color: #606266;
}
</style>
