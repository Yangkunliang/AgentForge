<script setup lang="ts">
import { uploadApi } from '@/api/modules/sessions'
import AssistantMessage from '@/components/chat/AssistantMessage.vue'
import ContextChips from '@/components/chat/ContextChips.vue'
import IntentSelector from '@/components/chat/IntentSelector.vue'
import ProjectBar from '@/components/chat/ProjectBar.vue'
import QuickActions from '@/components/chat/QuickActions.vue'
import SessionSidebar from '@/components/chat/SessionSidebar.vue'
import StagePreview from '@/components/chat/StagePreview.vue'
import WelcomeScreen from '@/components/chat/WelcomeScreen.vue'
import UserAvatar from '@/components/common/UserAvatar.vue'
import { useChat } from '@/composables/useChat'
import { usePipeline } from '@/composables/usePipeline'
import { useAdvancedSettingsStore } from '@/stores/advancedSettings'
import { useAgentStore } from '@/stores/agent'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import { useSessionStore } from '@/stores/session'
import { storeToRefs } from 'pinia'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const authStore = useAuthStore()
const agentStore = useAgentStore()
const projectStore = useProjectStore()
const advancedSettings = useAdvancedSettingsStore()
const { intent: currentIntent } = storeToRefs(advancedSettings)

const { getConfig, intentLabels } = usePipeline()

const currentConfig = computed(() => getConfig(currentIntent.value))
const showAdvancedPanel = ref(false)

const userName = computed(() => authStore.displayName)
const userAvatarUrl = computed(() => authStore.avatarUrl)

const inputText = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const sidebarVisible = ref(true)
const autoCreating = ref(false)
const sessionDrawerVisible = ref(false)

const sessionId = ref(route.params.sessionId as string | undefined)

const { sending, sendMessage: _send, abort: abortStream } = useChat()

// AI 助手信息（来自 store）
const agentInfo = computed(() => ({
  name: agentStore.myAgentSettings.agent_name,
  avatarUrl: agentStore.myAgentSettings.avatar_url || undefined,
}))

onMounted(async () => {
  await projectStore.fetchProjects()
  await sessionStore.fetchSessions(projectStore.currentProjectId)
  await agentStore.fetchMyAgentSettings()
  if (sessionId.value) {
    const session = sessionStore.sessions.find((s) => s.id === sessionId.value)
    if (session) {
      await sessionStore.selectSession(session)
    } else {
      sessionId.value = undefined
      router.replace('/chat')
    }
  }
})

// 折叠后 topbar 显示当前会话标题
const topbarTitle = computed(() => {
  if (!sidebarVisible.value && sessionStore.currentSession?.title) {
    return sessionStore.currentSession.title
  }
  return null
})

/** 格式化消息时间：今天只显示 HH:mm，跨天显示日期+时间 */
function formatMsgTime(isoStr: string): string {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (Number.isNaN(d.getTime())) return ''
  const now = new Date()
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  if (isToday) return `${hh}:${mm}`
  const M = d.getMonth() + 1
  const D = d.getDate()
  return `${M}月${D}日 ${hh}:${mm}`
}

// 从用户消息内容中提取图片 URL（markdown 格式 ![alt](url)）
function extractImages(content: string): Array<{ url: string; alt: string }> {
  if (!content) return []
  const regex = /!\[([^\]]*)\]\(([^)]+)\)/g
  const images: Array<{ url: string; alt: string }> = []
  let match
  while ((match = regex.exec(content)) !== null) {
    const url = match[2]
    // 只提取 http/https 开头的 URL，排除 base64
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/')) {
      images.push({ url, alt: match[1] || 'image' })
    }
  }
  return images
}

// 移除内容中的图片 markdown 标记，只保留纯文本
function stripImages(content: string): string {
  if (!content) return ''
  return content.replace(/!\[[^\]]*\]\([^)]+\)\n?/g, '').trim()
}

// 引导卡片填充话术到输入框
async function fillPrompt(text: string) {
  inputText.value = text
  await nextTick()
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
    textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 160) + 'px'
    textareaRef.value.focus()
  }
}

async function send() {
  const content = inputText.value.trim()
  if ((!content && pendingImages.value.length === 0) || sending.value || autoCreating.value) return

  if (!sessionId.value) {
    autoCreating.value = true
    try {
      const session = await sessionStore.createSession(projectStore.currentProjectId, currentIntent.value)
      sessionId.value = session.id
      router.replace(`/chat/${session.id}`)
    } catch {
      autoCreating.value = false
      return
    }
    autoCreating.value = false
  }

  // 上传图片到后端，获取 URL
  let finalContent = content
  if (pendingImages.value.length > 0) {
    const imageUrls: string[] = []
    for (const img of pendingImages.value) {
      try {
        const { data } = await uploadApi.image(img.file)
        imageUrls.push(data.url)
      } catch (err) {
        console.error('图片上传失败:', err)
      }
    }
    // 将图片 URL 以 markdown 格式拼入内容
    const imageTexts = imageUrls.map((url) => `![image](${url})`)
    if (imageTexts.length > 0) {
      finalContent = content
        ? `${content}\n\n${imageTexts.join('\n')}`
        : imageTexts.join('\n')
    }
  }

  inputText.value = ''
  pendingImages.value = []
  _send(finalContent, sessionId.value, advancedSettings.buildChatPayload())
}

function stopStreaming() {
  abortStream()
}

function onKeydown(e: KeyboardEvent) {
  // 输入法组合中（中文输入拼音时）跳过，避免拦截选词
  if (e.isComposing || e.keyCode === 229) {
    return
  }
  if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault()
    send()
  }
}

watch(
  () => sessionStore.messages.length,
  async () => {
    await nextTick()
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  },
)

watch(
  () => sessionStore.messages.map((m) => m.content).join(''),
  async () => {
    await nextTick()
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  },
)

watch(
  () => route.params.sessionId,
  async (id) => {
    sessionId.value = id as string | undefined
    if (id) {
      const session = sessionStore.sessions.find((s) => s.id === id)
      if (session) await sessionStore.selectSession(session)
    }
    sessionDrawerVisible.value = false
  },
)

watch(
  () => projectStore.currentProjectId,
  async (projectId, oldProjectId) => {
    if (projectId === oldProjectId) return
    await sessionStore.fetchSessions(projectId)
    if (sessionId.value && !sessionStore.sessions.some((session) => session.id === sessionId.value)) {
      sessionId.value = undefined
      router.replace('/chat')
    }
  },
)

async function handleNewChat() {
  const session = await sessionStore.createSession(projectStore.currentProjectId, currentIntent.value)
  router.push(`/chat/${session.id}`)
}

// ── 图片上传 ──────────────────────────────────────────────────
const pendingImages = ref<{ url: string; file: File }[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

function openFilePicker() {
  fileInputRef.value?.click()
}

function onFileChange(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files) return
  for (const file of Array.from(files)) {
    if (!file.type.startsWith('image/')) continue
    pendingImages.value.push({ url: URL.createObjectURL(file), file })
  }
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function removePendingImage(idx: number) {
  URL.revokeObjectURL(pendingImages.value[idx].url)
  pendingImages.value.splice(idx, 1)
}
</script>

<template>
  <div class="chat-layout">
    <!-- 桌面端：SessionSidebar 内联，支持折叠 -->
    <Transition name="sidebar">
      <SessionSidebar
        v-show="sidebarVisible"
        class="chat-sidebar-desktop"
        @collapse="sidebarVisible = false"
      />
    </Transition>

    <!-- 移动端：会话历史抄屉 -->
    <el-drawer
      v-model="sessionDrawerVisible"
      :with-header="false"
      direction="ltr"
      size="80%"
      class="session-drawer"
    >
      <SessionSidebar class="session-drawer-sidebar" @collapse="sessionDrawerVisible = false" />
    </el-drawer>

    <!-- 主区域 -->
    <div class="chat-main">
      <!-- 桌面端顶栏 -->
      <div class="chat-topbar chat-topbar--desktop">
        <button
          v-if="!sidebarVisible"
          class="topbar-btn"
          title="展开侧边栏"
          @click="sidebarVisible = true"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M13 9l3 3-3 3"/>
          </svg>
        </button>
        <span v-if="!sidebarVisible" class="topbar-divider" />

        <div class="topbar-info">
          <span class="topbar-slogan">全栈开发者的智能工作台</span>
          <span v-if="topbarTitle" class="topbar-session-title">{{ topbarTitle }}</span>
        </div>

        <div class="topbar-right">
          <ProjectBar />
        </div>
      </div>

      <!-- 移动端顶栏 -->
      <div class="chat-topbar chat-topbar--mobile">
        <button class="mobile-history-btn" @click="sessionDrawerVisible = true" title="会话历史">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span>历史</span>
        </button>
        <span class="session-name">{{ sessionStore.currentSession?.title ?? '新对话' }}</span>
        <button class="mobile-new-btn" @click="handleNewChat" title="新建对话">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>

      <!-- 消息区 -->
      <div ref="messagesEl" class="messages-area">
        <WelcomeScreen
          v-if="!sessionId || sessionStore.messages.length === 0"
          @prompt="fillPrompt"
        />

        <template v-for="msg in sessionStore.messages" :key="msg.id">
          <div v-if="msg.role === 'user'" class="user-message">
            <div class="user-msg-body">
              <div class="bubble">
                <div v-if="extractImages(msg.content).length" class="user-images">
                  <img v-for="img in extractImages(msg.content)" :key="img.url" :src="img.url" :alt="img.alt" class="user-image-thumb" />
                </div>
                <span v-if="stripImages(msg.content)">{{ stripImages(msg.content) }}</span>
              </div>
              <span v-if="msg.created_at && !msg.id.startsWith('local-')" class="msg-time">{{ formatMsgTime(msg.created_at) }}</span>
            </div>
            <div class="user-identity" :title="userName">
              <UserAvatar :name="userName" :avatar-url="userAvatarUrl" shape="circle" :size="32" />
              <span class="user-name">{{ userName }}</span>
            </div>
          </div>
          <AssistantMessage v-else :message="msg" :agent-name="agentInfo.name" :agent-avatar-url="agentInfo.avatarUrl" />
        </template>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <!-- 遮罩层：点击关闭弹窗 -->
        <div v-if="showAdvancedPanel" class="advanced-overlay" @click="showAdvancedPanel = false"></div>
        <!-- 高级设置面板（悬浮在输入区上方） -->
        <div class="advanced-panel" :class="{ 'advanced-panel--open': showAdvancedPanel }">
          <div class="advanced-panel__inner" @click.stop>
            <div class="advanced-panel__header">
              <span class="advanced-panel__title">高级设置</span>
              <button class="advanced-panel__close" @click="showAdvancedPanel = false">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div class="advanced-panel__content">

              <!-- 需求类型 -->
              <div class="ap-section">
                <span class="ap-section__label">需求类型</span>
                <IntentSelector v-model="currentIntent" />
              </div>

              <div class="ap-divider" />

              <!-- 上下文文件 -->
              <div class="ap-section">
                <span class="ap-section__label">上下文</span>
                <ContextChips />
              </div>

              <div class="ap-divider" />

              <!-- 执行流程 -->
              <div class="ap-section">
                <span class="ap-section__label">执行阶段</span>
                <StagePreview :intent="currentIntent" />
              </div>

              <div class="ap-divider" />

              <!-- 快捷动作 -->
              <div class="ap-section">
                <span class="ap-section__label">快捷动作</span>
                <QuickActions :actions="currentConfig.quickActions" @select="fillPrompt" />
              </div>

            </div>
          </div>
        </div>
        <div v-if="pendingImages.length > 0" class="pending-images">
          <div v-for="(img, idx) in pendingImages" :key="idx" class="pending-image">
            <img :src="img.url" :alt="img.file.name" />
            <button class="pending-image__remove" @click="removePendingImage(idx)">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <div class="input-box" :class="{ 'input-box--disabled': !sessionId }">
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*"
            multiple
            style="display: none"
            @change="onFileChange"
          />
          <button class="upload-btn" @click="openFilePicker" title="上传图片">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>

          <!-- 紧凑的需求类型选择器 -->
          <button class="intent-pill" @click="showAdvancedPanel = true">
            <span class="intent-pill__icon">{{ intentLabels[currentIntent].icon }}</span>
            <span class="intent-pill__label">{{ intentLabels[currentIntent].label }}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="intent-pill__arrow">
              <polyline points="6 15 12 9 18 15" />
            </svg>
          </button>

          <textarea
            ref="textareaRef"
            v-model="inputText"
            :placeholder="currentConfig.placeholder"
            :disabled="sending || autoCreating"
            rows="1"
            @keydown="onKeydown"
            @input="(e) => { const t = e.target as HTMLTextAreaElement; t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 160) + 'px' }"
          />

          <button class="advanced-btn" @click="showAdvancedPanel = true" title="高级设置">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>

          <button v-if="!sending" class="send-btn" :disabled="!inputText.trim() || autoCreating" @click="send">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2z" /></svg>
          </button>
          <button v-else class="stop-btn" @click="stopStreaming" title="停止生成">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
          </button>
        </div>
        <p class="input-hint">CodeSoul 由 AI 驱动，重要信息请以实际情况为准</p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chat-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: #fff;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

// ── 顶栏 ─────────────────────────────────────────────────────
.chat-topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  height: 52px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
  flex-shrink: 0;
}

.chat-topbar--desktop { display: flex; }
.chat-topbar--mobile  { display: none; }

.topbar-btn {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #9ca3af;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;

  &:hover { background: #f3f4f6; color: #374151; }
}

.topbar-divider {
  width: 1px;
  height: 16px;
  background: #e5e7eb;
  flex-shrink: 0;
}

.topbar-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
  flex: 1;
}

.topbar-slogan {
  font-size: 12px;
  color: #9ca3af;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.topbar-session-title {
  font-size: 13px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 1px;
}

.topbar-right {
  flex-shrink: 0;
}

// ── 侧边栏过渡动画 ────────────────────────────────────────────
.sidebar-enter-active,
.sidebar-leave-active {
  transition: width 0.22s ease, opacity 0.18s ease;
  overflow: hidden;
}
.sidebar-enter-from,
.sidebar-leave-to {
  width: 0 !important;
  opacity: 0;
}

// ── 消息区 ────────────────────────────────────────────────────
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.user-message {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 80%;
  align-self: flex-end;
  flex-direction: row-reverse;
}

.user-msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.msg-time {
  font-size: 11px;
  color: #9ca3af;
  padding: 0 2px;
}

.user-message {
  .bubble {
    background: #409eff;
    color: #fff;
    border-radius: 16px 4px 16px 16px;
    padding: 10px 14px;
    font-size: 14px;
    line-height: 1.6;
    word-break: break-word;
  }

  .user-images {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
  }

  .user-image-thumb {
    max-width: 200px;
    max-height: 200px;
    border-radius: 8px;
    object-fit: cover;
    cursor: zoom-in;
  }

  .user-identity {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .user-name {
    font-size: 11px;
    color: #9ca3af;
    white-space: nowrap;
    max-width: 56px;
    overflow: hidden;
    text-overflow: ellipsis;
    text-align: center;
  }
}

// ── 输入区 ────────────────────────────────────────────────────
.input-area {
  position: relative;
  padding: 16px 20px 20px;
  border-top: 1px solid #e5e7eb;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.advanced-overlay {
  position: fixed;
  inset: 0;
  z-index: 9;
  background: transparent;
}

// ── 高级设置面板（悬浮在输入区上方）───────────────────────────
.advanced-panel {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 0;
  overflow: hidden;
  opacity: 0;
  transform: translateY(8px);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
  pointer-events: none;

  &--open {
    max-height: 500px;
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }

  &__inner {
    background: #fff;
    border-radius: 12px 12px 0 0;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.08);
    border: 1px solid #f1f5f9;
    border-bottom: none;
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid #f1f5f9;
  }

  &__title {
    font-size: 13px;
    font-weight: 600;
    color: #475569;
  }

  &__close {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    background: #f1f5f9;
    border: none;
    color: #64748b;
    cursor: pointer;
    transition: all 0.15s;

    &:hover {
      background: #e2e8f0;
      color: #334155;
    }
  }

  &__content {
    padding: 0;
    max-height: 360px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }
}

// 面板分组（替代原 advanced-card）
.ap-section {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 10px 16px;

  &__label {
    font-size: 11px;
    font-weight: 500;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
    padding-top: 5px;
    width: 52px;
    flex-shrink: 0;
  }
}

.ap-divider {
  height: 1px;
  background: #f1f5f9;
  margin: 0 16px;
}

// ── 紧凑需求类型选择器（输入框内）───────────────────────────────
.intent-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: #eff6ff;
  border: 0.5px solid #bfdbfe;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #185FA5;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s;

  &:hover {
    background: #dbeafe;
    border-color: #93c5fd;
  }

  &__icon {
    font-size: 13px;
  }

  &__label {
    white-space: nowrap;
  }

  &__arrow {
    transition: transform 0.2s;

    &--up {
      transform: rotate(180deg);
    }
  }
}

.advanced-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid #e5e7eb;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;

  &:hover {
    background: #f3f4f6;
    color: #409eff;
    border-color: #bfdbfe;
  }
}

// ── 待发送图片预览 ────────────────────────────────────────────
.pending-images {
  display: flex;
  gap: 8px;
  padding: 8px 0;
  flex-wrap: wrap;
}

.pending-image {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e7eb;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  &__remove {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: rgba(0, 0, 0, .5);
    border: none;
    color: #fff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    &:hover { background: rgba(0, 0, 0, .7); }
  }
}

.input-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 8px 14px;
  transition: all 0.2s;

  &:focus-within {
    border-color: #3b82f6;
    background: #fff;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
  &--disabled { opacity: 0.6; }

  textarea {
    flex: 1;
    border: none;
    background: transparent;
    resize: none;
    font-size: 14px;
    line-height: 1.6;
    color: #1e293b;
    outline: none;
    min-height: 24px;
    max-height: 160px;
    overflow-y: auto;
    &::placeholder { color: #94a3b8; }
  }
}

.send-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: #409eff;
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s, transform 0.1s;

  &:hover:not(:disabled) {
    background: #337ecc;
    transform: translateY(-1px);
  }
  &:active:not(:disabled) { transform: translateY(0); }
  &:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }
}

.upload-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;

  &:hover {
    color: #3b82f6;
    background: #eff6ff;
  }
}

.stop-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: #ef4444;
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;

  &:hover { background: #dc2626; }
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: #9ca3af;
  margin: 8px 0 0;
}

// ── 移动端 ────────────────────────────────────────────────────
@media (max-width: $breakpoint-mobile) {
  .chat-sidebar-desktop { display: none !important; }
  .chat-topbar--desktop { display: none !important; }
  .chat-topbar--mobile  { display: flex !important; padding: 8px 12px; gap: 8px; }

  .session-name {
    font-size: 14px;
    font-weight: 500;
    text-align: center;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-history-btn,
  .mobile-new-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: none;
    cursor: pointer;
    color: #6b7280;
    padding: 6px 8px;
    border-radius: 6px;
    font-size: 13px;
    flex-shrink: 0;
    &:hover { background: #f3f4f6; }
  }

  .messages-area { padding: 16px 12px; }
  .input-area    { padding: 10px 12px 14px; }
  .input-hint    { display: none; }
  .user-message  { max-width: 90%; }

  .interaction-layer {
    .interaction-header {
      flex-direction: column;
      align-items: flex-start;
    }
  }
}

:deep(.session-drawer) {
  .el-drawer__body { padding: 0; overflow: hidden; }
}
.session-drawer-sidebar { height: 100%; }
</style>
