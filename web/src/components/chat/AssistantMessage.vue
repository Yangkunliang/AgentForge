<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { parseThinking, renderMarkdown } from '@/utils/markdown'
import UserAvatar from '@/components/common/UserAvatar.vue'
import type { ChatMessage } from '@/types'

// highlight.js 主题（GitHub 风格，亮色）
import 'highlight.js/styles/github.css'

const props = defineProps<{
  message: ChatMessage
  agentName?: string   // 当前对话绑定的 Agent 名称，未传则默认 'CodeSoul'
}>()

// AI 昵称：优先用 agentName，否则 'CodeSoul'
const aiName = computed(() => props.agentName?.trim() || 'CodeSoul')

// ── 思考过程 ─────────────────────────────────────────────────

const parsed = computed(() => parseThinking(props.message.content ?? ''))
const hasThinking = computed(() => !!parsed.value.thinking)
const thinkingExpanded = ref(false)
const thinkingDone = computed(() => props.message.content.includes('</think>'))

// 流式时思考过程自动展开；完成后自动折叠
watch(
  () => props.message.streaming,
  (streaming) => {
    if (streaming && hasThinking.value) thinkingExpanded.value = true
    if (!streaming) thinkingExpanded.value = false
  },
)

// ── 工具调用记录 ──────────────────────────────────────────────

const hasToolCalls = computed(() => !!(props.message.tool_calls && props.message.tool_calls.length > 0))
const toolCallsExpanded = ref(false)

// 流式时有工具调用自动展开；完成后自动折叠
watch(
  () => props.message.streaming,
  (streaming) => {
    if (streaming && hasToolCalls.value) toolCallsExpanded.value = true
    if (!streaming) toolCallsExpanded.value = false
  },
)

// ── 主体 Markdown 渲染 ────────────────────────────────────────

// 转义 HTML 特殊字符，防止流式期间粗精渲染 XSS
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const renderedBody = computed(() => {
  if (!parsed.value.body) return ''
  // 流式过程用纯文本占位，避免 markdown 解析不完整 token 导致 undefined
  if (props.message.streaming) {
    return `<p style="white-space:pre-wrap">${escapeHtml(parsed.value.body)}</p>`
  }
  return renderMarkdown(parsed.value.body)
})

const renderedThinking = computed(() => {
  if (!parsed.value.thinking) return ''
  if (props.message.streaming) {
    return `<p style="white-space:pre-wrap">${escapeHtml(parsed.value.thinking)}</p>`
  }
  return renderMarkdown(parsed.value.thinking)
})

// ── 长消息折叠 ────────────────────────────────────────────────

const COLLAPSE_THRESHOLD = 600  // px
const bodyRef = ref<HTMLElement | null>(null)
const collapsed = ref(false)
const collapsible = ref(false)

watch(renderedBody, async () => {
  if (props.message.streaming) return
  await new Promise(r => setTimeout(r, 50))  // 等 DOM 更新
  if (bodyRef.value && bodyRef.value.scrollHeight > COLLAPSE_THRESHOLD) {
    collapsible.value = true
    collapsed.value = true
  }
}, { flush: 'post' })

// ── 图片放大 ─────────────────────────────────────────────────

const zoomSrc = ref<string | null>(null)

function handleContentClick(e: MouseEvent) {
  const target = e.target as HTMLElement

  // 复制代码
  if (target.classList.contains('code-block__copy')) {
    const encoded = target.getAttribute('data-code') ?? ''
    navigator.clipboard.writeText(decodeURIComponent(encoded)).then(() => {
      target.textContent = '已复制'
      setTimeout(() => { target.textContent = '复制' }, 2000)
    })
    return
  }

  // 图片放大
  if (target.tagName === 'IMG' && target.hasAttribute('data-zoomable')) {
    zoomSrc.value = (target as HTMLImageElement).src
  }
}
</script>

<template>
  <div class="assistant-message">
    <UserAvatar :name="aiName" shape="squircle" :size="32" class="msg-avatar" />

    <div class="bubble">

      <!-- 思考中动画（无内容时） -->
      <div v-if="message.streaming && !message.content" class="thinking-dots">
        <span /><span /><span />
      </div>

      <!-- 思考过程折叠块 -->
      <div v-if="hasThinking" class="think-block" :class="{ 'think-block--done': thinkingDone }">
        <button class="think-block__toggle" @click="thinkingExpanded = !thinkingExpanded">
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2"
            :style="{ transform: thinkingExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform .2s' }"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          <span class="think-block__label">
            {{ thinkingDone ? '思考过程' : '思考中…' }}
          </span>
          <span v-if="message.streaming && !thinkingDone" class="think-block__spinner" />
        </button>

        <div v-show="thinkingExpanded" class="think-block__content">
          <div class="markdown-body" v-html="renderedThinking" @click="handleContentClick" />
        </div>
      </div>

      <!-- 工具调用记录折叠块 -->
      <div v-if="hasToolCalls" class="tool-calls-block">
        <button class="tool-calls-block__toggle" @click="toolCallsExpanded = !toolCallsExpanded">
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2"
            :style="{ transform: toolCallsExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform .2s' }"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          <span class="tool-calls-block__label">
            工具调用 ({{ message.tool_calls?.length }})
          </span>
        </button>

        <div v-show="toolCallsExpanded" class="tool-calls-block__content">
          <div v-for="(tc, idx) in message.tool_calls" :key="idx" class="tool-call-item">
            <div class="tool-call-item__header">
              <span class="tool-call-item__name">{{ tc.tool_name }}</span>
              <span class="tool-call-item__status" :class="`tool-call-item__status--${tc.status}`">
                {{ tc.status === 'running' ? '执行中' : tc.status === 'completed' ? '成功' : '失败' }}
              </span>
            </div>
            <div v-if="Object.keys(tc.arguments).length > 0" class="tool-call-item__args">
              <span class="tool-call-item__label">参数:</span>
              <pre class="tool-call-item__json">{{ JSON.stringify(tc.arguments, null, 2) }}</pre>
            </div>
            <div v-if="tc.result" class="tool-call-item__result">
              <span class="tool-call-item__label">结果:</span>
              <pre class="tool-call-item__json">{{ JSON.stringify(tc.result, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>

      <!-- 主体内容 -->
      <div
        v-if="parsed.body || !message.streaming"
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

        <!-- 折叠渐变遮罩 -->
        <div v-if="collapsed" class="collapse-mask" />
      </div>

      <!-- 展开 / 收起按钮 -->
      <button v-if="collapsible" class="collapse-toggle" @click="collapsed = !collapsed">
        {{ collapsed ? '展开全部 ↓' : '收起 ↑' }}
      </button>

      <!-- 流式光标 -->
      <span v-if="message.streaming && parsed.body" class="stream-cursor" />
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

.msg-avatar {
  margin-top: 2px;
  flex-shrink: 0;
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

// ── 思考中点动画 ─────────────────────────────────────────────
.thinking-dots {
  display: flex;
  gap: 4px;
  align-items: center;
  height: 22px;

  span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #9ca3af;
    animation: dot-bounce 1.2s infinite;

    &:nth-child(2) { animation-delay: .2s; }
    &:nth-child(3) { animation-delay: .4s; }
  }
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(.8); opacity: .5; }
  40%           { transform: scale(1.2); opacity: 1; }
}

// ── 工具调用记录折叠块 ────────────────────────────────────────
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

.tool-calls-block__label {
  flex: 1;
}

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

  &--running { background: #dbeafe; color: #1e40af; }
  &--completed { background: #dcfce7; color: #166534; }
  &--failed { background: #fee2e2; color: #991b1b; }
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

// ── 思考过程折叠块 ───────────────────────────────────────────
.think-block {
  margin-bottom: 10px;
  border: 1px solid #e0e0f0;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f8ff;

  &--done {
    border-color: #c7d2fe;
    background: #f5f3ff;
  }
}

.think-block__toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #6366f1;
  font-weight: 500;
  text-align: left;

  &:hover { background: rgba(99, 102, 241, .06); }
}

.think-block__label {
  flex: 1;
}

.think-block__spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #c7d2fe;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

.think-block__content {
  padding: 10px 14px 12px;
  border-top: 1px solid #e0e0f0;
  font-size: 13px;
  color: #6b7280;
  font-style: italic;
}

// ── 长消息折叠 ───────────────────────────────────────────────
.body-wrapper {
  position: relative;
  overflow: hidden;
  transition: max-height .3s ease;

  &:not(.body-wrapper--collapsed) {
    max-height: none !important;
  }
}

.collapse-mask {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
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
@keyframes spin   { to  { transform: rotate(360deg); } }

// ── 图片放大遮罩 ─────────────────────────────────────────────
</style>

<!-- 非 scoped：覆盖 v-html 内部元素 + highlight.js 代码块 -->
<style lang="scss">
// ── Markdown 主体排版 ────────────────────────────────────────
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

  // 任务列表（GFM）
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

  hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 1em 0;
  }

  a {
    color: #6366f1;
    text-decoration: none;

    &:hover { text-decoration: underline; }
  }

  // 行内代码
  .inline-code {
    background: #e8e8f0;
    padding: 1px 5px;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    color: #c7254e;
  }

  // 图片
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

// ── 代码块 ──────────────────────────────────────────────────
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

// ── 图片放大遮罩（Teleport 到 body，不能 scoped）────────────
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
