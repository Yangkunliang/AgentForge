<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  step: {
    type: 'code_execution'
    code: string
    status: 'running' | 'completed' | 'failed' | 'timeout'
    stdout: string
    stderr: string
    exit_code?: number
    duration_ms?: number
  }
}>()

// 超过 20 行可折叠
const MAX_COLLAPSE_LINES = 20
const codeLines = computed(() => props.step.code.split('\n'))
const codeCollapsible = computed(() => codeLines.value.length > MAX_COLLAPSE_LINES)
const codeCollapsed = ref(true)

// 状态徽章
const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  running:   { label: '执行中', cls: 'status--running' },
  completed: { label: '成功',   cls: 'status--completed' },
  failed:    { label: '失败',   cls: 'status--failed' },
  timeout:   { label: '超时',   cls: 'status--timeout' },
}

const status = computed(() => STATUS_MAP[props.step.status] ?? STATUS_MAP.running)

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

// 超时状态不显示代码区
const showCodeBlock = computed(() => props.step.status !== 'timeout')
</script>

<template>
  <div class="code-execution-card" :class="`code-execution-card--${step.status}`">
    <!-- Header -->
    <div class="code-execution-card__header">
      <span class="code-execution-card__icon">⚡</span>
      <span class="code-execution-card__label">执行代码</span>
      <span class="code-execution-card__status" :class="status.cls">
        {{ status.label }}
      </span>
      <span v-if="step.duration_ms" class="code-execution-card__duration">
        {{ step.duration_ms }}ms
      </span>
      <span v-if="step.status === 'running'" class="code-execution-card__spinner" />
    </div>

    <!-- 代码区（timeout 时不显示） -->
    <div v-if="showCodeBlock" class="code-execution-card__code">
      <div v-if="codeCollapsible" class="code-execution-card__code-toggle">
        <button @click="codeCollapsed = !codeCollapsed">
          {{ codeCollapsed ? `展开代码 (${codeLines.length} 行)` : '收起代码' }}
          <span :style="{ transform: codeCollapsed ? '' : 'rotate(180deg)', transition: 'transform .2s' }">
            ▾
          </span>
        </button>
      </div>
      <pre
        class="code-execution-card__code-text"
        :style="codeCollapsed ? { maxHeight: MAX_COLLAPSE_LINES * 1.6 + 'em' } : {}"
      ><code v-html="escapeHtml(step.code)" /></pre>
    </div>

    <!-- 超时提示 -->
    <div v-if="step.status === 'timeout'" class="code-execution-card__timeout">
      ⏱ 代码执行超时（超过 30 秒），请简化代码或检查死循环。
    </div>

    <!-- 运行中进度条 -->
    <div v-if="step.status === 'running'" class="code-execution-card__progress">
      <div class="code-execution-card__progress-bar" />
    </div>

    <!-- 输出区（仅 completed 状态） -->
    <div v-if="step.status === 'completed' && step.stdout" class="code-execution-card__output">
      <span class="code-execution-card__output-label">输出</span>
      <pre class="code-execution-card__output-text">{{ step.stdout }}</pre>
    </div>

    <!-- 警告区（stderr 非空） -->
    <div v-if="step.stderr" class="code-execution-card__warning">
      <span class="code-execution-card__output-label">警告</span>
      <pre class="code-execution-card__warning-text">{{ step.stderr }}</pre>
    </div>

    <!-- 错误区（exit_code != 0 且无 stderr 时） -->
    <div
      v-if="step.status === 'completed' && step.exit_code !== undefined && step.exit_code !== 0 && !step.stderr"
      class="code-execution-card__error"
    >
      <span class="code-execution-card__output-label">错误</span>
      <span>退出码: {{ step.exit_code }}</span>
    </div>

    <!-- 失败错误区 -->
    <div v-if="step.status === 'failed' && step.stderr" class="code-execution-card__error">
      <span class="code-execution-card__output-label">错误</span>
      <pre class="code-execution-card__error-text">{{ step.stderr }}</pre>
    </div>
  </div>
</template>

<style scoped lang="scss">
.code-execution-card {
  margin-bottom: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;

  &--running    { border-color: #93c5fd; background: #eff6ff; }
  &--completed  { border-color: #86efac; background: #f0fdf4; }
  &--failed     { border-color: #fca5a5; background: #fef2f2; }
  &--timeout    { border-color: #fde68a; background: #fffbeb; }
}

.code-execution-card__header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 13px;
  background: #f9fafb;
  border-bottom: 1px solid #f3f4f6;
}

.code-execution-card__icon {
  font-size: 15px;
}

.code-execution-card__label {
  font-weight: 600;
  color: #374151;
  font-size: 13px;
}

.code-execution-card__status {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
  margin-left: auto;

  &--running   { background: #dbeafe; color: #1e40af; }
  &--completed { background: #dcfce7; color: #166534; }
  &--failed    { background: #fee2e2; color: #991b1b; }
  &--timeout   { background: #fef3c7; color: #92400e; }
}

.code-execution-card__duration {
  font-size: 11px;
  color: #9ca3af;
}

.code-execution-card__spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #93c5fd;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

// ── 代码区 ──────────────────────────────────────────────────────
.code-execution-card__code {
  border-bottom: 1px solid #f3f4f6;
}

.code-execution-card__code-toggle {
  padding: 6px 12px;
  background: #f0f0f0;
  border-bottom: 1px solid #e5e7eb;

  button {
    font-size: 12px;
    color: #6366f1;
    background: none;
    border: none;
    cursor: pointer;
    font-family: monospace;

    &:hover { text-decoration: underline; }
  }
}

.code-execution-card__code-text {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
  font-family: 'Consolas', 'Monaco', monospace;
  color: #1e293b;
  white-space: pre;
  background: #f8fafc;
}

// ── 超时 ────────────────────────────────────────────────────────
.code-execution-card__timeout {
  padding: 12px 14px;
  font-size: 13px;
  color: #92400e;
  background: #fef3c7;
  border-top: 1px solid #fde68a;
}

// ── 进度条 ──────────────────────────────────────────────────────
.code-execution-card__progress {
  height: 2px;
  background: #e5e7eb;
}

.code-execution-card__progress-bar {
  height: 100%;
  width: 30%;
  background: #2563eb;
  animation: progress-slide 1.4s ease-in-out infinite;
}

// ── 输出/警告/错误区 ───────────────────────────────────────────
.code-execution-card__output,
.code-execution-card__warning,
.code-execution-card__error {
  padding: 8px 14px;
  font-size: 12px;
  line-height: 1.5;
  border-top: 1px solid #f3f4f6;
}

.code-execution-card__output-label {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
  margin-right: 4px;
}

.code-execution-card__output {
  background: #f0fdf4;
  border-left: 3px solid #22c55e;
  padding-left: 11px;
}

.code-execution-card__output-text {
  margin: 4px 0 0;
  font-family: 'Consolas', 'Monaco', monospace;
  color: #166534;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-execution-card__warning {
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  padding-left: 11px;
}

.code-execution-card__warning-text {
  margin: 4px 0 0;
  font-family: 'Consolas', 'Monaco', monospace;
  color: #92400e;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-execution-card__error {
  background: #fef2f2;
  border-left: 3px solid #ef4444;
  padding-left: 11px;
}

.code-execution-card__error-text {
  margin: 4px 0 0;
  font-family: 'Consolas', 'Monaco', monospace;
  color: #991b1b;
  white-space: pre-wrap;
  word-break: break-word;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes progress-slide {
  0%   { transform: translateX(-100%); }
  50%  { transform: translateX(100%); }
  100% { transform: translateX(100%); }
}
</style>
