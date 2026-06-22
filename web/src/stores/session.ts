import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sessionsApi } from '@/api/modules/sessions'
import type { Session, ChatMessage } from '@/types'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const currentSession = ref<Session | null>(null)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)

  async function fetchSessions() {
    const { data } = await sessionsApi.list()
    sessions.value = data
  }

  async function createSession(): Promise<Session> {
    const { data } = await sessionsApi.create()
    sessions.value.unshift(data)
    return data
  }

  async function selectSession(session: Session) {
    currentSession.value = session
    loading.value = true
    try {
      const { data } = await sessionsApi.messages(session.id)
      messages.value = data
    } finally {
      loading.value = false
    }
  }

  async function renameSession(id: string, title: string) {
    const { data } = await sessionsApi.rename(id, title)
    const idx = sessions.value.findIndex((s) => s.id === id)
    if (idx !== -1) sessions.value[idx] = data
    if (currentSession.value?.id === id) currentSession.value = data
  }

  async function deleteSession(id: string) {
    await sessionsApi.delete(id)
    sessions.value = sessions.value.filter((s) => s.id !== id)
    if (currentSession.value?.id === id) {
      currentSession.value = null
      messages.value = []
    }
  }

  /** 追加用户消息到本地（乐观更新），返回占位 assistant 消息 */
  function appendUserMessage(content: string): ChatMessage {
    const userMsg: ChatMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    const assistantMsg: ChatMessage = {
      id: `local-assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      streaming: true,
    }
    messages.value.push(userMsg, assistantMsg)
    return assistantMsg
  }

  /** SSE 流式追加 assistant 内容 */
  function appendStreamChunk(localId: string, chunk: string) {
    const msg = messages.value.find((m) => m.id === localId)
    if (msg) msg.content += chunk
  }

  /** SSE 完成后，用真实内容替换占位消息 */
  function finalizeAssistantMessage(localId: string, content: string) {
    const msg = messages.value.find((m) => m.id === localId)
    if (msg) {
      msg.content = content
      msg.streaming = false
    }
  }

  /** 追加工具调用记录 */
  function appendToolCall(
    localId: string,
    toolName: string,
    args: Record<string, unknown>,
    status: 'running' | 'completed' | 'failed',
    result?: Record<string, unknown>,
  ) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    if (!msg.tool_calls) msg.tool_calls = []
    
    const existing = msg.tool_calls.find((tc) => tc.tool_name === toolName)
    if (existing) {
      existing.status = status
      if (result) existing.result = result
    } else {
      msg.tool_calls.push({ tool_name: toolName, arguments: args, status, result })
    }
  }

  /** 将当前会话置顶（发送消息后调用）*/
  function bumpCurrentSession() {
    if (!currentSession.value) return
    const idx = sessions.value.findIndex((s) => s.id === currentSession.value!.id)
    if (idx > 0) {
      const [session] = sessions.value.splice(idx, 1)
      sessions.value.unshift(session)
    }
  }

  return {
    sessions,
    currentSession,
    messages,
    loading,
    fetchSessions,
    createSession,
    selectSession,
    renameSession,
    deleteSession,
    appendUserMessage,
    appendStreamChunk,
    finalizeAssistantMessage,
    appendToolCall,
    bumpCurrentSession,
  }
})
