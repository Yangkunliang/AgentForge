<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '@/api'
import type {
  DashboardStats,
  LLMUsageStats,
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
const emptyLLMUsageStats: LLMUsageStats = {
  total_calls: 0,
  tokens_used: 0,
  cost_usd: 0,
  average_latency_ms: 0,
  by_model_route: [],
  by_stage: [],
}

const skillAuthorizationStats = computed(() => (
  stats.value?.evaluation.skill_authorizations ?? emptySkillAuthorizationStats
))
const llmUsageStats = computed(() => stats.value?.evaluation.llm ?? emptyLLMUsageStats)
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

function formatTokens(tokens: number): string {
  return new Intl.NumberFormat('zh-CN').format(tokens)
}

function formatLatency(latencyMs: number): string {
  if (latencyMs >= 1000) {
    const seconds = latencyMs / 1000
    return `${seconds.toFixed(Number.isInteger(seconds) ? 0 : 1)} s`
  }
  return `${Math.round(latencyMs)} ms`
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
            <div class="card__header">任务费用（今日）</div>
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

      <section class="card llm-usage" data-testid="llm-usage-panel">
        <div class="llm-usage__header">
          <div class="card__header">LLM 实际用量</div>
          <span class="llm-usage__scope">累计</span>
        </div>

        <div class="llm-usage__metrics">
          <div class="llm-metric llm-metric--calls" data-testid="llm-total-calls">
            <span class="llm-metric__label">已记录调用</span>
            <strong class="llm-metric__value">{{ formatTokens(llmUsageStats.total_calls) }}</strong>
          </div>
          <div class="llm-metric llm-metric--cost" data-testid="llm-total-cost">
            <span class="llm-metric__label">累计成本</span>
            <strong class="llm-metric__value">${{ formatCost(llmUsageStats.cost_usd) }}</strong>
          </div>
          <div class="llm-metric llm-metric--tokens" data-testid="llm-total-tokens">
            <span class="llm-metric__label">Token</span>
            <strong class="llm-metric__value">{{ formatTokens(llmUsageStats.tokens_used) }}</strong>
          </div>
          <div class="llm-metric llm-metric--latency" data-testid="llm-average-latency">
            <span class="llm-metric__label">平均延迟</span>
            <strong class="llm-metric__value">{{ formatLatency(llmUsageStats.average_latency_ms) }}</strong>
          </div>
        </div>

        <div class="llm-usage__rankings">
          <section class="llm-ranking" aria-labelledby="llm-route-ranking-title">
            <div class="llm-ranking__header">
              <h2 id="llm-route-ranking-title">按 ModelRoute</h2>
              <span>调用 / Token / 成本</span>
            </div>
            <div v-if="llmUsageStats.by_model_route.length === 0" class="llm-ranking__empty">
              暂无 LLM 调用记录
            </div>
            <div
              v-for="item in llmUsageStats.by_model_route"
              :key="item.model_route_key"
              class="llm-ranking__row"
            >
              <span class="llm-ranking__name" :title="item.name">{{ item.name }}</span>
              <span class="llm-ranking__calls">{{ item.total_calls }} 次</span>
              <span class="llm-ranking__tokens">{{ formatTokens(item.tokens_used) }}</span>
              <span class="llm-ranking__cost">${{ formatCost(item.cost_usd) }}</span>
            </div>
          </section>

          <section class="llm-ranking" aria-labelledby="llm-stage-ranking-title">
            <div class="llm-ranking__header">
              <h2 id="llm-stage-ranking-title">按 Stage</h2>
              <span>调用 / Token / 成本</span>
            </div>
            <div v-if="llmUsageStats.by_stage.length === 0" class="llm-ranking__empty">
              暂无 LLM 调用记录
            </div>
            <div
              v-for="item in llmUsageStats.by_stage"
              :key="item.stage_id"
              class="llm-ranking__row"
            >
              <span class="llm-ranking__name" :title="item.name">{{ item.name }}</span>
              <span class="llm-ranking__calls">{{ item.total_calls }} 次</span>
              <span class="llm-ranking__tokens">{{ formatTokens(item.tokens_used) }}</span>
              <span class="llm-ranking__cost">${{ formatCost(item.cost_usd) }}</span>
            </div>
          </section>
        </div>
      </section>

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

.llm-usage {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $spacing-md;
  }

  &__scope {
    color: #73767a;
    font-size: 12px;
  }

  &__metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    overflow: hidden;
    border: 1px solid #e4e7ed;
    border-radius: $border-radius-sm;
  }

  &__rankings {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: $spacing-xl;
    margin-top: $spacing-lg;
  }
}

.llm-metric {
  min-width: 0;
  min-height: 96px;
  padding: $spacing-md $spacing-lg;
  border-top: 3px solid #606266;
  border-right: 1px solid #e4e7ed;
  background: #fff;

  &:last-child {
    border-right: 0;
  }

  &--calls {
    border-top-color: #2563eb;
  }

  &--cost {
    border-top-color: #0f766e;
  }

  &--tokens {
    border-top-color: #b45309;
  }

  &--latency {
    border-top-color: #52525b;
  }

  &__label {
    display: block;
    margin-bottom: $spacing-sm;
    color: #73767a;
    font-size: 13px;
  }

  &__value {
    display: block;
    overflow-wrap: anywhere;
    color: #1f2937;
    font-size: 24px;
    font-variant-numeric: tabular-nums;
    font-weight: 650;
    line-height: 1.2;
  }
}

.llm-ranking {
  min-width: 0;

  &__header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: $spacing-md;
    min-height: 30px;
    padding-bottom: $spacing-sm;
    border-bottom: 1px solid #dcdfe6;

    h2 {
      margin: 0;
      color: #303133;
      font-size: 14px;
      font-weight: 600;
    }

    span {
      color: #a0a4aa;
      font-size: 11px;
      white-space: nowrap;
    }
  }

  &__empty {
    display: flex;
    align-items: center;
    min-height: 116px;
    color: #909399;
    font-size: 13px;
  }

  &__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 52px 72px 84px;
    align-items: center;
    gap: $spacing-sm;
    min-height: 40px;
    border-bottom: 1px solid #f0f2f5;
    color: #606266;
    font-size: 13px;
    font-variant-numeric: tabular-nums;

    &:last-child {
      border-bottom: 0;
    }
  }

  &__name {
    overflow: hidden;
    color: #303133;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__calls,
  &__tokens,
  &__cost {
    text-align: right;
    white-space: nowrap;
  }

  &__cost {
    color: #0f766e;
    font-weight: 600;
  }
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
  .llm-usage {
    &__metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    &__rankings {
      grid-template-columns: 1fr;
      gap: $spacing-lg;
    }
  }

  .llm-metric {
    &:nth-child(2) {
      border-right: 0;
    }

    &:nth-child(-n + 2) {
      border-bottom: 1px solid #e4e7ed;
    }
  }

  .llm-ranking__row {
    grid-template-areas:
      "name cost"
      "calls tokens";
    grid-template-columns: minmax(0, 1fr) auto;
    gap: $spacing-xs $spacing-sm;
    padding: $spacing-sm 0;
  }

  .llm-ranking {
    &__name {
      grid-area: name;
    }

    &__calls {
      grid-area: calls;
      text-align: left;
    }

    &__tokens {
      grid-area: tokens;
    }

    &__cost {
      grid-area: cost;
    }
  }

  .auth-metrics {
    &__summary,
    &__rank-grid {
      grid-template-columns: 1fr;
    }
  }
}
</style>
