<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import UserAvatar from '@/components/common/UserAvatar.vue'
import ExecutionProgressBar from './ExecutionProgressBar.vue'
import ExecutionStepList from './ExecutionStepList.vue'
import type { ChatMessage } from '@/types'

// highlight.js 主题（GitHub 风格，亮色）
import 'highlight.js/styles/github.css'

const props = defineProps<{
  message: ChatMessage
  agentName?: string
  agentAvatarUrl?: string
}>()

const aiName = computed(() => props.agentName?.trim() || 'CodeSoul')

// ── Execution Steps（TASK-009）────────────────────────────────
// execution_steps 存在时走新渲染路径；
// 旧 tool_calls 字段作为兜底，兼容历史消息
const hasExecutionSteps = computed(
  () => !!(props.message.execution_steps && props.message.execution_steps.length > 0),
)
const hasLegacyToolCalls = computed(
  () => !hasExecutionSteps.value &&
    !!(props.message.tool_calls && props.message.tool_calls.length > 0),
)
const legacyToolCallsExpanded = ref(true)

watch(
  () => props.message.streaming,
  (streaming) => {
    if (!streaming) legacyToolCallsExpanded.value = false
  },
)

// ── 主体 Markdown 渲染 ────────────────────────────────────────
// 新路径：content 是纯正文（thinking 由独立事件推送，不再内嵌标签）
// 旧路径兜底：如果 content 还含有 <thinking> 标签，剥离后渲染

function stripThinkingTags(text: string): string {
  return text.replace(/<thinking>[\s\S]*?<\/thinking>\s*/g, '').trim()
}

const bodyText = computed(() => stripThinkingTags(props.message.content ?? ''))

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const renderedBody = computed(() => {
  if (!bodyText.value) return ''
  if (props.message.streaming) {
    return `<p style="white-space:pre-wrap">${escapeHtml(bodyText.value)}</p>`
  }
  return renderMarkdown(bodyText.value)
})

// ── 长消息折叠 ────────────────────────────────────────────────
const COLLAPSE_THRESHOLD = 600
const bodyRef = ref<HTMLElement | null>(null)
const collapsed = ref(false)
const collapsible = ref(false)

watch(renderedBody, async () => {
  if (props.message.streaming) return
  await new Promise(r => setTimeout(r, 50))
  if (bodyRef.value && bodyRef.value.scrollHeight > COLLAPSE_THRESHOLD) {
    collapsible.value = true
    collapsed.value = true
  }
}, { flush: 'post' })

// ── 图片放大 ─────────────────────────────────────────────────
const zoomSrc = ref<string | null>(null)

function handleContentClick(e: MouseEvent) {
  const target = e.target as HTMLElement

  if (target.classList.contains('code-block__copy')) {
    const encoded = target.getAttribute('data-code') ?? ''
    navigator.clipboard.writeText(decodeURIComponent(encoded)).then(() => {
      target.textContent = '已复制'
      setTimeout(() => { target.textContent = '复制' }, 2000)
    })
    return
  }

  if (target.tagName === 'IMG' && target.hasAttribute('data-zoomable')) {
    zoomSrc.value = (target as HTMLImageElement).src
  }
}
</script>

<template>
  <div class="assistant-message">
    <div class="ai-identity">
      <UserAvatar :name="aiName" :avatar-url="props.agentAvatarUrl" shape="squircle" :size="32" />
      <span class="ai-name">{{ aiName }}</span>
    </div>

    <div class="bubble">

      <!-- 流式进度条（streaming 时显示） -->
      <ExecutionProgressBar :streaming="!!message.streaming" />

      <!-- 思考中提示（无内容且无步骤时显示粒子旋转动画） -->
      <div
        v-if="message.streaming && !bodyText && !hasExecutionSteps"
        class="thinking-hint"
      >
        <span class="thinking-hint__text">正在思考中</span>
        <div class="thinking-hint__particles">
          <span class="particle" />
          <span class="particle" />
          <span class="particle" />
        </div>
      </div>

      <!-- ── 新路径：execution_steps 可视化（TASK-009）──────── -->
      <ExecutionStepList
        v-if="hasExecutionSteps"
        :steps="message.execution_steps!"
        :streaming="!!message.streaming"
      />

      <!-- ── 旧路径兜底：历史消息 tool_calls（JSON 展示）────── -->
      <div v-if="hasLegacyToolCalls" class="tool-calls-block">
        <button class="tool-calls-block__toggle" @click="legacyToolCallsExpanded = !legacyToolCallsExpanded">
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2"
            :style="{ transform: legacyToolCallsExpanded ? 'rotate(90deg)' : '', transition: 'transform .2s' }"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          <span class="tool-calls-block__label">
            工具调用 ({{ message.tool_calls?.length }})
          </span>
        </button>

        <div v-show="legacyToolCallsExpanded" class="tool-calls-block__content">
          <div v-for="(tc, idx) in message.tool_calls" :key="idx" class="tool-call-item">
            <div class="tool-call-item__header">
              <span class="tool-call-item__name">{{ tc.tool_name }}</span>
              <span class="tool-call-item__status" :class="`tool-call-item__status--${tc.status}`">
                {{ tc.status === 'running' ? '执行中' : tc.status === 'completed' ? '成功' : '失败' }}
              </span>
            </div>
            <div v-if="Object.keys(tc.arguments).length > 0" class="tool-call-item__args">
              <span class="tool-call-item__label">参数</span>
              <pre class="tool-call-item__json">{{ JSON.stringify(tc.arguments, null, 2) }}</pre>
            </div>
            <div v-if="tc.result" class="tool-call-item__result">
              <span class="tool-call-item__label">结果</span>
              <pre class="tool-call-item__json">{{ JSON.stringify(tc.result, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>

      <!-- 主体内容 -->
      <div
        v-if="bodyText || !message.streaming"
        class="body-wrapper"
        :class="{ 'body-wrapper--collapsed': collapsed }"
        :style="collapsed ? { maxHeight: COLLAPSE_THRESHOLD + 'px' } : {}"
      >
        <div
          ref="bodyRef"
          class="markdown-body"
          v-html="renderedBody"
          @click="handleContentClick"
        />
        <div v-if="collapsed" class="collapse-mask" />
      </div>

      <!-- 展开 / 收起 -->
      <button v-if="collapsible" class="collapse-toggle" @click="collapsed = !collapsed">
        {{ collapsed ? '展开全部 ↓' : '收起 ↑' }}
      </button>

      <!-- 流式光标 -->
      <span v-if="message.streaming && bodyText" class="stream-cursor" />
    </div>

    <!-- 图片放大遮罩 -->
    <Teleport to="body">
      <div v-if="zoomSrc" class="image-zoom-overlay" @click="zoomSrc = null">
        <img :src="zoomSrc" class="image-zoom-img" />
        <button class="image-zoom-close">✕</button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped lang="scss">
.assistant-message {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 85%;
  align-self: flex-start;
}

.ai-identity {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  margin-top: 2px;
}

.ai-name {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}

.bubble {
  background: #f4f4f5;
  border-radius: 4px 16px 16px 16px;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.7;
  color: #1a1a1a;
  word-break: break-word;
  min-width: 40px;
}

// ── 思考中粒子旋转动画 ────────────────────────────────────
.thinking-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 4px 0 6px;
  min-height: 28px;
}

.thinking-hint__text {
  font-size: 13px;
  color: #9ca3af;
  letter-spacing: 0.01em;
  font-weight: 500;
}

.thinking-hint__particles {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 2px;
}

.particle {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  opacity: 0;
  animation: particle-orbit 2s ease-in-out infinite;

  &:nth-child(1) {
    background: #c7d2fe;
    animation-delay: 0s;
  }
  &:nth-child(2) {
    background: #a5b4fc;
    animation-delay: 0.6s;
  }
  &:nth-child(3) {
    background: #818cf8;
    animation-delay: 1.2s;
  }
}

@keyframes particle-orbit {
  0% {
    opacity: 0;
    transform: scale(0.5) translateY(0);
  }
  25% {
    opacity: 1;
    transform: scale(1.1) translateY(-4px);
  }
  50% {
    opacity: 0.8;
    transform: scale(1) translateY(0);
  }
  75% {
    opacity: 1;
    transform: scale(0.8) translateY(4px);
  }
  100% {
    opacity: 0;
    transform: scale(0.5) translateY(0);
  }
}

// ── 旧路径 tool_calls 折叠块（历史消息兜底）────────────────────
.tool-calls-block {
  margin-bottom: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #f9fafb;
}

.tool-calls-block__toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #374151;
  font-weight: 500;
  text-align: left;

  &:hover { background: rgba(55, 65, 81, .06); }
}

.tool-calls-block__label { flex: 1; }

.tool-calls-block__content {
  padding: 10px 14px 12px;
  border-top: 1px solid #e5e7eb;
}

.tool-call-item {
  padding: 8px;
  border-radius: 6px;
  background: #fff;
  margin-bottom: 8px;
  border: 1px solid #f3f4f6;
  &:last-child { margin-bottom: 0; }
}

.tool-call-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.tool-call-item__name {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  font-family: 'Monaco', 'Menlo', monospace;
}

.tool-call-item__status {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  &--running   { background: #dbeafe; color: #1e40af; }
  &--completed { background: #dcfce7; color: #166534; }
  &--failed    { background: #fee2e2; color: #991b1b; }
}

.tool-call-item__label {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
  margin-right: 6px;
}

.tool-call-item__args,
.tool-call-item__result {
  font-size: 12px;
  color: #4b5563;
  margin-top: 4px;
}

.tool-call-item__json {
  margin: 4px 0 0;
  padding: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  font-size: 11px;
  color: #374151;
  overflow-x: auto;
  white-space: pre;
}

// ── 长消息折叠 ───────────────────────────────────────────────
.body-wrapper {
  position: relative;
  overflow: hidden;
  transition: max-height .3s ease;
  &:not(.body-wrapper--collapsed) { max-height: none !important; }
}

.collapse-mask {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 80px;
  background: linear-gradient(transparent, #f4f4f5);
  pointer-events: none;
}

.collapse-toggle {
  display: block;
  margin-top: 8px;
  background: none;
  border: none;
  color: #6366f1;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  &:hover { text-decoration: underline; }
}

// ── 流式光标 ─────────────────────────────────────────────────
.stream-cursor {
  display: inline-block;
  width: 2px;
  height: 15px;
  background: #6366f1;
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 1s step-end infinite;
}

@keyframes blink { 50% { opacity: 0; } }
</style>

<!-- 非 scoped：覆盖 v-html 内部 + highlight.js -->
<style lang="scss">
.markdown-body {
  h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    margin: 1em 0 .4em;
    line-height: 1.35;
    color: #111827;
  }
  h1 { font-size: 1.4em; }
  h2 { font-size: 1.2em; }
  h3 { font-size: 1.05em; }

  p { margin: .5em 0; }

  ul, ol {
    padding-left: 1.5em;
    margin: .5em 0;
    li { margin: .25em 0; }
  }

  input[type="checkbox"] {
    margin-right: 6px;
    vertical-align: middle;
  }

  blockquote {
    margin: .5em 0;
    padding: 6px 12px;
    border-left: 3px solid #c7d2fe;
    color: #6b7280;
    background: #f5f3ff;
    border-radius: 0 4px 4px 0;
  }

  table {
    border-collapse: collapse;
    width: 100%;
    margin: .75em 0;
    font-size: 13px;

    th, td {
      border: 1px solid #e5e7eb;
      padding: 6px 12px;
      text-align: left;
    }
    th { background: #f3f4f6; font-weight: 600; }
    tr:nth-child(even) td { background: #fafafa; }
  }

  hr { border: none; border-top: 1px solid #e5e7eb; margin: 1em 0; }

  a {
    color: #6366f1;
    text-decoration: none;
    &:hover { text-decoration: underline; }
  }

  .inline-code {
    background: #e8e8f0;
    padding: 1px 5px;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    color: #c7254e;
  }

  .chat-image {
    max-width: 100%;
    border-radius: 6px;
    margin: .5em 0;
    cursor: zoom-in;
    border: 1px solid #e5e7eb;
    transition: opacity .15s;
    &:hover { opacity: .9; }
  }
}

.code-block {
  margin: .75em 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  background: #f6f8fa;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 12px;
    background: #f0f0f0;
    border-bottom: 1px solid #e5e7eb;
  }

  &__lang {
    font-size: 11px;
    color: #6b7280;
    font-family: monospace;
    text-transform: uppercase;
    letter-spacing: .05em;
  }

  &__copy {
    font-size: 11px;
    color: #6366f1;
    background: none;
    border: 1px solid #c7d2fe;
    border-radius: 4px;
    padding: 2px 8px;
    cursor: pointer;
    transition: background .15s;
    &:hover { background: #e0e7ff; }
  }

  pre {
    margin: 0;
    padding: 14px 16px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.6;
    code { background: none; padding: 0; font-size: inherit; }
  }
}

.image-zoom-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, .85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  cursor: zoom-out;
  padding: 24px;
}

.image-zoom-img {
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 6px;
  object-fit: contain;
  box-shadow: 0 20px 60px rgba(0, 0, 0, .5);
}

.image-zoom-close {
  position: fixed;
  top: 20px;
  right: 24px;
  background: rgba(255, 255, 255, .15);
  border: none;
  color: #fff;
  font-size: 18px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  &:hover { background: rgba(255, 255, 255, .25); }
}
</style>
