<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  step: {
    type: 'tool_call'
    tool_name: string
    arguments: Record<string, unknown>
    status: 'running' | 'completed' | 'failed' | 'timeout'
    result?: Record<string, unknown>
    duration_ms?: number
  }
}>()

// 工具图标映射
const TOOL_ICONS: Record<string, string> = {
  get_weather: '🌤',
  web_search: '🔍',
  http_request: '🌐',
  update_profile: '👤',
  code_executor: '⚡',
}

const icon = computed(() => TOOL_ICONS[props.step.tool_name] ?? '🔧')

// 状态徽章
const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  running:   { label: '执行中', cls: 'status--running' },
  completed: { label: '成功',   cls: 'status--completed' },
  failed:    { label: '失败',   cls: 'status--failed' },
  timeout:   { label: '超时',   cls: 'status--failed' },
}

const status = computed(() => STATUS_MAP[props.step.status] ?? STATUS_MAP.running)

// 参数摘要：避免裸 JSON，按工具定制
function formatArgsSummary(): string {
  const args = props.step.arguments
  const name = props.step.tool_name

  if (name === 'code_executor' && args.code) {
    const code = String(args.code)
    const lines = code.split('\n')
    return lines.length > 5
      ? `代码预览（${lines.length} 行）: ${code.slice(0, 120)}...`
      : code
  }

  if (name === 'web_search' && args.query) {
    return `搜索: "${String(args.query)}"`
  }

  if (name === 'get_weather') {
    return `地点: ${String(args.location ?? args.city ?? args.query ?? '未知')}`
  }

  if (name === 'http_request' && args.url) {
    return `${String(args.method ?? 'GET')} ${String(args.url)}`
  }

  if (name === 'update_profile') {
    const fields = Object.keys(args).filter(k => k !== 'user_id')
    return `更新字段: ${fields.join(', ')}`
  }

  // 兜底：展示前 3 个 key
  const keys = Object.keys(args)
  if (keys.length === 0) return '—'
  if (keys.length <= 3) {
    return keys.map(k => `${k}: ${JSON.stringify(args[k]).slice(0, 80)}`).join(' | ')
  }
  return `${keys.length} 个参数，展示前 3 个`
}

// 结果摘要
function formatResultSummary(): string | null {
  const result = props.step.result
  if (!result || Object.keys(result).length === 0) return null
  const name = props.step.tool_name

  if (name === 'get_weather' && result.temperature) {
    return `气温 ${result.temperature}°${result.unit ?? ''}，${result.description ?? '晴'}`
  }

  if (name === 'web_search' && result.results) {
    const count = Array.isArray(result.results) ? result.results.length : 0
    return `找到 ${count} 条结果`
  }

  if (name === 'http_request') {
    const code = result.status_code ?? result.code
    return `HTTP ${code}`
  }

  // 兜底：展示前 3 个 key
  const keys = Object.keys(result)
  if (keys.length <= 5) {
    return keys.map(k => `${k}: ${JSON.stringify(result[k]).slice(0, 120)}`).join('\n')
  }
  return `${keys.length} 个字段，摘要: ${keys.slice(0, 3).join(', ')}`
}

const argsSummary = computed(() => formatArgsSummary())
const resultSummary = computed(() => formatResultSummary())
</script>

<template>
  <div class="tool-call-card" :class="`tool-call-card--${step.status}`">
    <!-- Header -->
    <div class="tool-call-card__header">
      <span class="tool-call-card__icon">{{ icon }}</span>
      <span class="tool-call-card__name">{{ step.tool_name }}</span>
      <span class="tool-call-card__status" :class="status.cls">
        {{ status.label }}
      </span>
      <span v-if="step.duration_ms" class="tool-call-card__duration">
        {{ step.duration_ms }}ms
      </span>
      <span v-if="step.status === 'running'" class="tool-call-card__spinner" />
    </div>

    <!-- 参数区 -->
    <div v-if="argsSummary" class="tool-call-card__args">
      <pre class="tool-call-card__args-text">{{ argsSummary }}</pre>
    </div>

    <!-- 结果区 -->
    <div v-if="resultSummary" class="tool-call-card__result">
      <span class="tool-call-card__result-label">结果</span>
      <pre class="tool-call-card__result-text">{{ resultSummary }}</pre>
    </div>
  </div>
</template>

<style scoped lang="scss">
.tool-call-card {
  margin-bottom: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;

  &--running  { border-color: #93c5fd; background: #eff6ff; }
  &--completed { border-color: #86efac; background: #f0fdf4; }
  &--failed,
  &--timeout  { border-color: #fca5a5; background: #fef2f2; }
}

.tool-call-card__header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 13px;
  background: #f9fafb;
  border-bottom: 1px solid #f3f4f6;
}

.tool-call-card__icon {
  font-size: 15px;
}

.tool-call-card__name {
  font-weight: 600;
  color: #374151;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.tool-call-card__status {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
  margin-left: auto;

  &--running   { background: #dbeafe; color: #1e40af; }
  &--completed { background: #dcfce7; color: #166534; }
  &--failed    { background: #fee2e2; color: #991b1b; }
}

.tool-call-card__duration {
  font-size: 11px;
  color: #9ca3af;
}

.tool-call-card__spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #93c5fd;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

.tool-call-card__args,
.tool-call-card__result {
  padding: 8px 12px;
  font-size: 12px;
  color: #4b5563;
}

.tool-call-card__args {
  border-bottom: 1px solid #f3f4f6;
}

.tool-call-card__result-label {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
  margin-right: 4px;
}

.tool-call-card__args-text,
.tool-call-card__result-text {
  margin: 4px 0 0;
  padding: 8px;
  background: #f9fafb;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
