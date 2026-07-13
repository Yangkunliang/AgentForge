<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '@/api'
import type {
  DashboardStats,
  SkillAuthorizationByPermission,
  SkillAuthorizationBySkill,
  SkillAuthorizationStats,
} from '@/types'

const router = useRouter()
const stats = ref<DashboardStats | null>(null)
const loading = ref(false)
const emptySkillAuthorizationStats: SkillAuthorizationStats = {
  required: 0,
  granted: 0,
  grant_rate: 0,
  by_skill: [],
  by_permission: [],
}

const skillAuthorizationStats = computed(() => (
  stats.value?.evaluation.skill_authorizations ?? emptySkillAuthorizationStats
))
const grantRateWidth = computed(() => `${Math.min(Math.max(skillAuthorizationStats.value.grant_rate, 0), 1) * 100}%`)
const topAuthorizedSkills = computed(() => skillAuthorizationStats.value.by_skill.slice(0, 3))
const topAuthorizedPermissions = computed(() => skillAuthorizationStats.value.by_permission.slice(0, 3))

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

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(rate === 0 || rate === 1 ? 0 : 1)}%`
}

function formatAuthRatio(item: SkillAuthorizationBySkill | SkillAuthorizationByPermission): string {
  return `${item.granted}/${item.required}`
}

function permissionLabel(permission: string): string {
  const labels: Record<string, string> = {
    credential: 'credential',
    external_side_effect: 'external_side_effect',
    project_context: 'project_context',
    shell: 'shell',
  }
  return labels[permission] ?? permission
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

      <div class="card auth-metrics">
        <div class="card__header">高风险 Skill 授权</div>
        <div class="auth-metrics__summary">
          <div class="auth-metrics__item">
            <span class="auth-metrics__value">{{ skillAuthorizationStats.required }}</span>
            <span class="auth-metrics__label">请求</span>
          </div>
          <div class="auth-metrics__item">
            <span class="auth-metrics__value">{{ skillAuthorizationStats.granted }}</span>
            <span class="auth-metrics__label">已授权</span>
          </div>
          <div class="auth-metrics__item">
            <span class="auth-metrics__value">{{ formatPercent(skillAuthorizationStats.grant_rate) }}</span>
            <span class="auth-metrics__label">通过率</span>
          </div>
        </div>
        <div class="auth-metrics__bar" aria-hidden="true">
          <div class="auth-metrics__bar-fill" :style="{ width: grantRateWidth }" />
        </div>
        <div class="auth-metrics__rank-grid">
          <section class="auth-rank">
            <div class="auth-rank__title">按 Skill</div>
            <div v-if="topAuthorizedSkills.length === 0" class="auth-rank__empty">暂无授权记录</div>
            <div
              v-for="item in topAuthorizedSkills"
              :key="item.skill_name"
              class="auth-rank__row"
            >
              <span class="auth-rank__name" :title="item.skill_name">{{ item.skill_name }}</span>
              <span class="auth-rank__ratio">{{ formatAuthRatio(item) }}</span>
              <span class="auth-rank__rate">{{ formatPercent(item.grant_rate) }}</span>
            </div>
          </section>
          <section class="auth-rank">
            <div class="auth-rank__title">按 Permission</div>
            <div v-if="topAuthorizedPermissions.length === 0" class="auth-rank__empty">暂无授权记录</div>
            <div
              v-for="item in topAuthorizedPermissions"
              :key="item.permission"
              class="auth-rank__row"
            >
              <span class="auth-rank__name" :title="item.permission">{{ permissionLabel(item.permission) }}</span>
              <span class="auth-rank__ratio">{{ formatAuthRatio(item) }}</span>
              <span class="auth-rank__rate">{{ formatPercent(item.grant_rate) }}</span>
            </div>
          </section>
        </div>
      </div>

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

.auth-metrics {
  &__summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: $spacing-md;
    margin-bottom: $spacing-md;
  }

  &__item {
    min-width: 0;
    padding: $spacing-md;
    border: 1px solid #ebeef5;
    border-radius: $border-radius-sm;
    background: #fafbfc;
  }

  &__value {
    display: block;
    margin-bottom: $spacing-xs;
    color: #303133;
    font-size: 26px;
    font-weight: 600;
    line-height: 1.1;
    word-break: break-word;
  }

  &__label {
    color: #909399;
    font-size: 13px;
  }

  &__bar {
    height: 8px;
    overflow: hidden;
    border-radius: 999px;
    background: #edf1f7;
  }

  &__bar-fill {
    height: 100%;
    border-radius: inherit;
    background: #409eff;
    transition: width 0.2s ease;
  }

  &__rank-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: $spacing-md;
    margin-top: $spacing-md;
  }
}

.auth-rank {
  min-width: 0;

  &__title {
    margin-bottom: $spacing-sm;
    color: #606266;
    font-size: 13px;
    font-weight: 600;
  }

  &__empty {
    display: flex;
    align-items: center;
    min-height: 42px;
    color: #909399;
    font-size: 13px;
  }

  &__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    align-items: center;
    gap: $spacing-sm;
    min-height: 36px;
    border-bottom: 1px solid #f0f2f5;
    font-size: 14px;

    &:last-child {
      border-bottom: 0;
    }
  }

  &__name {
    overflow: hidden;
    color: #303133;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__ratio {
    color: #606266;
    font-variant-numeric: tabular-nums;
  }

  &__rate {
    min-width: 48px;
    color: #409eff;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: $breakpoint-mobile) {
  .auth-metrics {
    &__summary,
    &__rank-grid {
      grid-template-columns: 1fr;
    }
  }
}
</style>
