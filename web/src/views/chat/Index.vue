<script setup lang="ts">
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useChat } from '@/composables/useChat'
import SessionSidebar from '@/components/chat/SessionSidebar.vue'
import AssistantMessage from '@/components/chat/AssistantMessage.vue'
import type { ChatMessage } from '@/types'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()

const inputText = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const sidebarVisible = ref(true)
const autoCreating = ref(false)

// 当前会话 ID 从路由取
const sessionId = ref(route.params.sessionId as string | undefined)

const { sending, sendMessage: _send } = useChat()
async function send() {
  const content = inputText.value.trim()
  if (!content || sending.value || autoCreating.value) return

  // 没有有效 sessionId 时，自动创建一个新会话
  if (!sessionId.value) {
    autoCreating.value = true
    try {
      const session = await sessionStore.createSession()
      sessionId.value = session.id
      router.replace(`/chat/${session.id}`)
    } catch {
      autoCreating.value = false
      return
    }
    autoCreating.value = false
  }

  inputText.value = ''
  await _send(content, sessionId.value)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
    e.preventDefault()
    send()
  }
}

// 消息变化时自动滚底
watch(
  () => sessionStore.messages.length,
  async () => {
    await nextTick()
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  },
)

// 流式追加时也滚底
watch(
  () => sessionStore.messages.map((m) => m.content).join(''),
  async () => {
    await nextTick()
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  },
)

onMounted(async () => {
  await sessionStore.fetchSessions()

  if (sessionId.value) {
    // 校验 sessionId 是否真实存在
    const session = sessionStore.sessions.find((s) => s.id === sessionId.value)
    if (session) {
      await sessionStore.selectSession(session)
    } else {
      // ID 无效（已删除或伪造），清除路由回到空白还
      sessionId.value = undefined
      router.replace('/chat')
    }
  }
})

// 路由切换时同步 sessionId
watch(
  () => route.params.sessionId,
  async (id) => {
    sessionId.value = id as string | undefined
    if (id) {
      const session = sessionStore.sessions.find((s) => s.id === id)
      if (session) await sessionStore.selectSession(session)
    }
  },
)

async function handleNewChat() {
  const session = await sessionStore.createSession()
  router.push(`/chat/${session.id}`)
}

// ── 图片上传 ────────────────────────────────────────────────
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
    const url = URL.createObjectURL(file)
    pendingImages.value.push({ url, file })
  }
  // reset input
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function removePendingImage(idx: number) {
  URL.revokeObjectURL(pendingImages.value[idx].url)
  pendingImages.value.splice(idx, 1)
}
</script>

<template>
  <div class="chat-layout">
    <!-- 侧边栏 -->
    <SessionSidebar v-show="sidebarVisible" />

    <!-- 主区域 -->
    <div class="chat-main">
      <!-- 顶栏 -->
      <div class="chat-topbar">
        <button class="toggle-sidebar" @click="sidebarVisible = !sidebarVisible" title="切换侧边栏">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <span class="session-name">{{ sessionStore.currentSession?.title ?? 'AgentForge' }}</span>
      </div>

      <!-- 消息区 -->
      <div ref="messagesEl" class="messages-area">
        <!-- 空状态 -->
        <div v-if="!sessionId || sessionStore.messages.length === 0" class="welcome">
          <div class="welcome-icon">✦</div>
          <h2>有什么可以帮你的？</h2>
          <p>输入任何问题，多 Agent 将协同为你处理</p>
        </div>

        <!-- 消息气泡 -->
        <template v-for="msg in sessionStore.messages" :key="msg.id">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="user-message">
            <div class="bubble">
              <div v-if="msg.images?.length" class="user-images">
                <img
                  v-for="img in msg.images"
                  :key="img.url"
                  :src="img.url"
                  :alt="img.alt"
                  class="user-image-thumb"
                />
              </div>
              <span v-if="msg.content">{{ msg.content }}</span>
            </div>
            <div class="avatar">我</div>
          </div>

          <!-- AI 消息 -->
          <AssistantMessage v-else :message="msg" />
        </template>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <div class="input-box" :class="{ 'input-box--disabled': !sessionId }">
          <textarea
            v-model="inputText"
            :placeholder="'输入消息，Enter 发送 / Shift+Enter 换行'"
            :disabled="sending || autoCreating"
            rows="1"
            @keydown="onKeydown"
            @input="(e) => { const t = e.target as HTMLTextAreaElement; t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 160) + 'px' }"
          />
          <button
            class="send-btn"
            :disabled="!inputText.trim() || sending || autoCreating"
            @click="send"
          >
            <svg v-if="!sending" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 21l21-9L2 3v7l15 2-15 2z" />
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
              <circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" />
            </svg>
          </button>
        </div>
        <p class="input-hint">AgentForge 由 AI 驱动，重要信息请以实际情况为准</p>
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

// 顶栏
.chat-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
  z-index: 1;

  .toggle-sidebar {
    background: none;
    border: none;
    cursor: pointer;
    color: #6b7280;
    display: flex;
    align-items: center;
    padding: 4px;
    border-radius: 4px;

    &:hover { background: #f3f4f6; }
  }

  .session-name {
    font-size: 14px;
    font-weight: 500;
    color: #111827;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

// 消息区
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  text-align: center;
  padding: 60px 0;

  .welcome-icon {
    font-size: 48px;
    color: #6366f1;
    margin-bottom: 16px;
  }

  h2 {
    font-size: 22px;
    font-weight: 600;
    color: #111827;
    margin: 0 0 8px;
  }

  p {
    font-size: 14px;
    margin: 0;
  }
}

// 用户消息气泡
.user-message {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 80%;
  align-self: flex-end;
  flex-direction: row-reverse;

  .bubble {
    background: #6366f1;
    color: #fff;
    border-radius: 16px 4px 16px 16px;
    padding: 10px 14px;
    font-size: 14px;
    line-height: 1.6;
    word-break: break-word;
  }

  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #e5e7eb;
    color: #374151;
    font-size: 12px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
}

// 输入区
.input-area {
  padding: 16px 20px 20px;
  border-top: 1px solid #e5e7eb;
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px 12px;
  transition: border-color 0.15s;

  &:focus-within {
    border-color: #6366f1;
    background: #fff;
  }

  &--disabled {
    opacity: 0.6;
  }

  textarea {
    flex: 1;
    border: none;
    background: transparent;
    resize: none;
    font-size: 14px;
    line-height: 1.5;
    color: #111827;
    outline: none;
    min-height: 24px;
    max-height: 160px;
    overflow-y: auto;

    &::placeholder { color: #9ca3af; }
  }
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #6366f1;
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;

  &:hover:not(:disabled) { background: #4f46e5; }
  &:disabled { background: #c7d2fe; cursor: not-allowed; }
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: #9ca3af;
  margin: 8px 0 0;
}

// 移动端
@media (max-width: 768px) {
  .chat-layout {
    position: relative;
  }
}
</style>
