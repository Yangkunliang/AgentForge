import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sessionsApi } from '@/api/modules/sessions'
import type { Session, ChatMessage, ExecutionStep, ThinkingStep, ToolCallStep, CodeExecutionStep } from '@/types'

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

  // ── Execution Steps 操作（TASK-009）──────────────────────────

  /** 确保消息带有 execution_steps 数组，返回引用 */
  function _ensureSteps(msg: ChatMessage): ExecutionStep[] {
    if (!msg.execution_steps) msg.execution_steps = []
    return msg.execution_steps
  }

  /** 追加新步骤到消息 */
  function _appendStep(msg: ChatMessage, step: ExecutionStep) {
    _ensureSteps(msg).push(step)
  }

  /** 找到消息当前正在运行的步骤（最后一个 running 步骤）*/
  function _findRunningStep(msg: ChatMessage, type?: string): ExecutionStep | undefined {
    const steps = msg.execution_steps ?? []
    for (let i = steps.length - 1; i >= 0; i--) {
      const s = steps[i]
      if (s.type === 'running' || s.status === 'running') {
        if (!type || s.type === type) return s
      }
    }
    return undefined
  }

  // ── Thinking ────────────────────────────────────────────────

  function startThinkingStep(localId: string) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    _appendStep(msg, { type: 'thinking', content: '', streaming: true })
  }

  function appendThinkingDelta(localId: string, delta: string) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    const steps = msg.execution_steps ?? []
    for (let i = steps.length - 1; i >= 0; i--) {
      const s = steps[i]
      if (s.type === 'thinking' && s.streaming) {
        s.content += delta
        return
      }
    }
    // 兜底：创建一个新的 thinking 步骤
    _appendStep(msg, { type: 'thinking', content: delta, streaming: true })
  }

  function endThinkingStep(localId: string, durationMs: number) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    const steps = msg.execution_steps ?? []
    for (let i = steps.length - 1; i >= 0; i--) {
      const s = steps[i]
      if (s.type === 'thinking' && s.streaming) {
        s.streaming = false
        s.duration_ms = durationMs
        return
      }
    }
  }

  // ── Tool Call ───────────────────────────────────────────────

  function startToolCallStep(localId: string, toolName: string, args: Record<string, unknown>) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    _appendStep(msg, {
      type: 'tool_call',
      tool_name: toolName,
      arguments: args,
      status: 'running',
    })
  }

  function completeToolCallStep(
    localId: string,
    toolName: string,
    result: Record<string, unknown>,
    durationMs?: number,
  ) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    const steps = msg.execution_steps ?? []
    for (let i = steps.length - 1; i >= 0; i--) {
      const s = steps[i]
      if (s.type === 'tool_call' && s.status === 'running' && s.tool_name === toolName) {
        s.status = 'completed'
        s.result = result
        if (durationMs) s.duration_ms = durationMs
        return
      }
    }
  }

  function failToolCallStep(localId: string, toolName: string, error: string) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    const steps = msg.execution_steps ?? []
    for (let i = steps.length - 1; i >= 0; i--) {
      const s = steps[i]
      if (s.type === 'tool_call' && s.tool_name === toolName && s.status === 'running') {
        s.status = 'failed'
        s.result = { error }
        return
      }
    }
  }

  // ── Code Execution ──────────────────────────────────────────

  function startCodeExecution(localId: string, code: string) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    _appendStep(msg, {
      type: 'code_execution',
      code,
      status: 'running',
      stdout: '',
      stderr: '',
    })
  }

  function completeCodeExecution(
    localId: string,
    stdout: string,
    stderr: string,
    exitCode: number,
    durationMs: number,
  ) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    const steps = msg.execution_steps ?? []
    for (let i = steps.length - 1; i >= 0; i--) {
      const s = steps[i]
      if (s.type === 'code_execution' && s.status === 'running') {
        s.status = 'completed'
        s.stdout = stdout
        s.stderr = stderr
        s.exit_code = exitCode
        s.duration_ms = durationMs
        return
      }
    }
  }

  function failCodeExecution(localId: string, reason: string) {
    const msg = messages.value.find((m) => m.id === localId)
    if (!msg) return
    const steps = msg.execution_steps ?? []
    for (let i = steps.length - 1; i >= 0; i--) {
      const s = steps[i]
      if (s.type === 'code_execution' && s.status !== 'completed') {
        s.status = reason === 'timeout' ? 'timeout' : 'failed'
        s.stderr = reason === 'timeout'
          ? `执行超时（超过 30 秒），请简化代码或检查死循环。`
          : reason
        return
      }
    }
  }

  // ── 旧版 appendToolCall（向后兼容）────────────────────────────

  /** 废弃：内部迁移到新 actions，保留导出避免编译报错 */
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
    // Execution Steps
    startThinkingStep,
    appendThinkingDelta,
    endThinkingStep,
    startToolCallStep,
    completeToolCallStep,
    failToolCallStep,
    startCodeExecution,
    completeCodeExecution,
    failCodeExecution,
    // Legacy
    appendToolCall,
    bumpCurrentSession,
  }
})
