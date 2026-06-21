<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useSessionStore } from '@/stores/session'
import type { Session } from '@/types'

const emit = defineEmits<{ (e: 'collapse'): void }>()

const router = useRouter()
const sessionStore = useSessionStore()

const editingId = ref<string | null>(null)
const editingTitle = ref('')

async function handleNew() {
  const session = await sessionStore.createSession()
  await sessionStore.selectSession(session)
  router.push(`/chat/${session.id}`)
}

async function handleSelect(session: Session) {
  await sessionStore.selectSession(session)
  router.push(`/chat/${session.id}`)
}

function startRename(session: Session) {
  editingId.value = session.id
  editingTitle.value = session.title
}

async function confirmRename(id: string) {
  const title = editingTitle.value.trim()
  if (title) await sessionStore.renameSession(id, title)
  editingId.value = null
}

async function handleDelete(session: Session) {
  await ElMessageBox.confirm(`删除「${session.title}」？此操作不可恢复。`, '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await sessionStore.deleteSession(session.id)
  ElMessage.success('会话已删除')
  if (!sessionStore.currentSession) router.push('/chat')
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString()
}
</script>

<template>
  <aside class="session-sidebar">
    <!-- Header: CodeSoul + 折叠按钮 -->
    <div class="sidebar-header">
      <span class="sidebar-brand">CodeSoul</span>
      <button class="collapse-btn" title="折叠侧边栏" @click="emit('collapse')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 9l-3 3 3 3"/>
        </svg>
      </button>
    </div>

    <!-- 新建对话 -->
    <div class="new-chat-wrap">
      <button class="new-chat-btn" @click="handleNew">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建对话
      </button>
    </div>

    <!-- 会话列表 -->
    <div class="session-list">
      <div
        v-for="session in sessionStore.sessions"
        :key="session.id"
        class="session-item"
        :class="{ 'session-item--active': sessionStore.currentSession?.id === session.id }"
        @click="handleSelect(session)"
      >
        <template v-if="editingId === session.id">
          <input
            v-model="editingTitle"
            class="rename-input"
            autofocus
            @keyup.enter="confirmRename(session.id)"
            @keyup.esc="editingId = null"
            @blur="confirmRename(session.id)"
            @click.stop
          />
        </template>
        <template v-else>
          <span class="session-title">{{ session.title }}</span>
          <span class="session-time">{{ formatTime(session.updated_at) }}</span>
          <div class="session-actions" @click.stop>
            <button title="重命名" @click="startRename(session)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
            <button title="删除" class="delete-btn" @click="handleDelete(session)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                <path d="M10 11v6M14 11v6" /><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
              </svg>
            </button>
          </div>
        </template>
      </div>

      <div v-if="sessionStore.sessions.length === 0" class="empty-hint">
        还没有对话，点击上方按钮开始
      </div>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.session-sidebar {
  width: 220px;
  height: 100%;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

// ── Header ───────────────────────────────────────────────────
.sidebar-header {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.sidebar-brand {
  font-size: 15px;
  font-weight: 600;
  color: #409eff;
  letter-spacing: 0.01em;
}

.collapse-btn {
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
  transition: background 0.15s, color 0.15s;

  &:hover {
    background: #f3f4f6;
    color: #374151;
  }
}

// ── New chat ─────────────────────────────────────────────────
.new-chat-wrap {
  padding: 10px 10px 8px;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border: 1px dashed #d1d5db;
  border-radius: $border-radius-md;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  color: #6b7280;
  transition: background 0.15s, border-color 0.15s;

  &:hover {
    background: #f9fafb;
    border-color: #9ca3af;
  }
}

// ── Session list ─────────────────────────────────────────────
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 6px 16px;
}

.session-item {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 9px 10px;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: #f3f4f6;
    .session-actions { opacity: 1; }
  }

  &--active {
    background: #eff6ff;
    .session-title { color: #409eff; font-weight: 500; }
  }
}

.session-title {
  font-size: 13px;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.session-time {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 2px;
}

.session-actions {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;

  button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 3px;
    border-radius: 4px;
    color: #6b7280;
    display: flex;
    align-items: center;

    &:hover { background: #e5e7eb; color: #111; }
  }

  .delete-btn:hover { color: #ef4444; }
}

.rename-input {
  width: 100%;
  font-size: 13px;
  border: 1px solid #409eff;
  border-radius: 4px;
  padding: 2px 6px;
  outline: none;
}

.empty-hint {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  padding: 32px 16px;
}
</style>
