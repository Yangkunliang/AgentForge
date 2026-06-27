/**
 * useChat — 封装「发消息 → 订阅 SSE → 流式更新气泡」完整流程
 *
 * 多 Agent 的执行细节对用户透明：
 * - 用户只看到"AI 思考中..." → 文字逐步出现 → 完成
 * - task_started / bid_received / agent_assigned 等内部事件静默忽略
 * - 只有 llm_response（流式片段）和 task_completed（最终结果）影响 UI
 *
 * TASK-009 SSE 事件映射
 * ─────────────────────
 * thinking_start/delta/end    → sessionStore.start/append/endThinkingStep
 * sandbox_executing           → sessionStore.startCodeExecution
 * sandbox_completed/timeout   → sessionStore.complete/failCodeExecution
 * tool_call_start/end         → code_executor → CodeExecutionStep
 *                             → 其他工具 → ToolCallStep
 */
import { ref } from 'vue'
import { sessionsApi } from '@/api/modules/sessions'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'
import type { SSEEvent } from '@/types'

export function useChat(sessionId?: string) {
  const sessionStore = useSessionStore()
  const sending = ref(false)
  let currentController: AbortController | null = null

  async function sendMessage(content: string, id?: string): Promise<AbortController | null> {
    const targetId = id ?? sessionId
    if (!content.trim() || sending.value || !targetId) return null
    sending.value = true

    // 乐观更新：立即显示用户消息 + 空 assistant 占位
    const assistantMsg = sessionStore.appendUserMessage(content)
    const localId = assistantMsg.id

    try {
      // ── 本地意图拦截（昵称 / 头像设置，直接前端处理）────────
      const intercepted = await _tryIntercept(content, localId)
      if (intercepted) {
        sending.value = false
        sessionStore.bumpCurrentSession()
        return null
      }

      // 发送到后端，获取 task_id
      const { data } = await sessionsApi.chat(targetId, content)
      const taskId = data.task_id

      // 订阅 SSE，监听执行过程
      currentController = await _subscribeSSE(taskId, localId)

      // 更新会话排序（置顶）
      sessionStore.bumpCurrentSession()
    } catch (err) {
      sessionStore.finalizeAssistantMessage(localId, '发送失败，请重试。')
    } finally {
      sending.value = false
    }

    return currentController
  }

  function abort() {
    currentController?.abort()
    currentController = null
  }

  return { sending, sendMessage, abort }
}

// ── 本地意图拦截 ─────────────────────────────────────────────
/**
 * 识别用户想通过对话设置自己昵称的意图，直接调用 authStore.updateProfile()
 * 并流式"打字"回复，模拟 AI 响应。
 *
 * 支持的指令格式（自然语言，宽松匹配）：
 *   "把我的昵称改成 XXX"
 *   "帮我设置昵称为 XXX"
 *   "我的昵称叫 XXX"
 *   "/set-nickname XXX"（快捷指令）
 *
 * 返回 true 表示已拦截，false 表示需要走后端
 */
async function _tryIntercept(content: string, localId: string): Promise<boolean> {
  const authStore = useAuthStore()
  const sessionStore = useSessionStore()

  const text = content.trim()

  // ── 1. 昵称设置 ────────────────────────────────────────────
  const nicknamePatterns = [
    /(?:把我的昵称|我的昵称|帮我.{0,4}昵称|设置昵称|修改昵称|昵称改)[：:为成叫是\s]*["「『]?([^\s"」』,，。！？\n]{1,20})["」』]?/,
    /\/set-nickname\s+(.+)/i,
    /(?:call me|my nickname is|set nickname to)\s+(.+)/i,
  ]

  for (const pattern of nicknamePatterns) {
    const m = text.match(pattern)
    if (m) {
      const newNickname = m[1].trim().replace(/^["'「『]|["'」』]$/g, '')
      if (!newNickname || newNickname.length > 50) continue

      // 流式打字回复
      const reply = `好的！我已经把你的昵称设置为「**${newNickname}**」了 🎉\n\n以后就叫你 ${newNickname} 啦，有什么需要帮忙的尽管说~`
      await _typeReply(localId, reply, sessionStore)

      // 调用 store 更新
      try {
        await authStore.updateProfile({ nickname: newNickname })
      } catch {
        // 已在 store 内 ElMessage.error，这里静默
      }
      return true
    }
  }

  // ── 2. 清除昵称 ────────────────────────────────────────────
  if (/(?:清除|删除|取消|去掉|移除).{0,6}昵称|reset nickname/i.test(text)) {
    const reply = `已经帮你把昵称清除了，之后会用你的账号用户名「**${authStore.user?.username}**」显示。`
    await _typeReply(localId, reply, sessionStore)
    try { await authStore.updateProfile({ nickname: null }) } catch { /* silent */ }
    return true
  }

  // ── 3. 查询当前昵称 ────────────────────────────────────────
  if (/我的昵称是什么|当前昵称|查看昵称/.test(text)) {
    const name = authStore.user?.nickname
    const reply = name
      ? `你当前的昵称是「**${name}**」。想改的话，说「把我的昵称改成 XX」就行。`
      : `你还没有设置昵称，当前显示的是你的用户名「**${authStore.user?.username}**」。\n\n想设置的话，说「把我的昵称改成 XX」就行~`
    await _typeReply(localId, reply, sessionStore)
    return true
  }

  return false
}

/**
 * 模拟流式打字效果写入 assistant 气泡
 */
async function _typeReply(
  localId: string,
  text: string,
  sessionStore: ReturnType<typeof useSessionStore>,
): Promise<void> {
  // 标记为流式开始（显示打点动画）
  sessionStore.appendStreamChunk(localId, '')

  // 按字符分批输出，模拟打字
  const chars = [...text]  // 支持 emoji 和中文
  const BATCH = 3          // 每批输出字符数
  const DELAY = 18         // ms / 批

  for (let i = 0; i < chars.length; i += BATCH) {
    await new Promise<void>(r => setTimeout(r, DELAY))
    sessionStore.appendStreamChunk(localId, chars.slice(i, i + BATCH).join(''))
  }

  // 流式结束，最终化消息
  sessionStore.finalizeAssistantMessage(localId, text)
}

async function _subscribeSSE(taskId: string, localAssistantId: string): Promise<AbortController> {
  const sessionStore = useSessionStore()
  const token = localStorage.getItem('access_token')
  if (!token) {
    return new AbortController()
  }

  const controller = new AbortController()

  return new Promise<AbortController>((resolve) => {
    fetch(`/api/v1/sse/tasks/${taskId}/stream`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok || !response.body) {
          sessionStore.finalizeAssistantMessage(localAssistantId, '连接失败，请重试。')
          resolve(controller)
          return
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const chunks = buffer.split('\n\n')
          buffer = chunks.pop() ?? ''

          for (const chunk of chunks) {
            const event = _parseSSE(chunk)
            if (!event) {
              if (chunk.trim()) console.log('[SSE] unparsed chunk:', JSON.stringify(chunk))
              continue
            }

            console.log('[SSE] event:', event.event, 'data:', JSON.stringify(event.data))

            switch (event.event) {
              // ── Thinking ───────────────────────────────────────────
              case 'thinking_start': {
                sessionStore.startThinkingStep(localAssistantId)
                break
              }

              case 'thinking_delta': {
                const delta = (event.data.delta as string) ?? ''
                sessionStore.appendThinkingDelta(localAssistantId, delta)
                break
              }

              case 'thinking_end': {
                const duration_ms = (event.data.duration_ms as number) ?? 0
                sessionStore.endThinkingStep(localAssistantId, duration_ms)
                break
              }

              // ── 沙箱代码执行 ───────────────────────────────────────
              case 'sandbox_executing': {
                const code = (event.data.code as string) ?? ''
                sessionStore.startCodeExecution(localAssistantId, code)
                break
              }

              case 'sandbox_completed': {
                // sandbox_completed 只携带 exit_code + duration_ms，
                // 完整 stdout/stderr 由 task_completed 携带的 content 覆盖
                const exit_code = (event.data.exit_code as number) ?? 0
                const duration_ms = (event.data.duration_ms as number) ?? 0
                sessionStore.completeCodeExecution(
                  localAssistantId, '', '', exit_code, duration_ms,
                )
                break
              }

              case 'sandbox_timeout': {
                sessionStore.failCodeExecution(localAssistantId, 'timeout')
                break
              }

              // ── 流式文字片段（LLM 逐 token 输出）───────────────────
              case 'llm_response': {
                const delta = (event.data.delta as string) ?? ''
                sessionStore.appendStreamChunk(localAssistantId, delta)
                break
              }

              // ── 工具调用 ───────────────────────────────────────────
              case 'tool_call_start': {
                const toolName = event.data.tool_name as string
                const args = event.data.arguments as Record<string, unknown>
                sessionStore.startToolCallStep(localAssistantId, toolName, args)
                break
              }

              case 'tool_call_end': {
                const toolName = event.data.tool_name as string
                const args = event.data.arguments as Record<string, unknown>
                const result = event.data.result as Record<string, unknown>

                // code_executor 的 tool_call_end 只携带耗时信息，
                // 完整 stdout/stderr 已在 sandbox_completed 中填充
                if (toolName === 'code_executor') {
                  const duration_ms = (event.data.duration_ms as number) ?? 0
                  const stdout = (result?.stdout as string) ?? ''
                  const stderr = (result?.stderr as string) ?? ''
                  const exit_code = (result?.exit_code as number) ?? 0
                  sessionStore.completeCodeExecution(
                    localAssistantId, stdout, stderr, exit_code, duration_ms,
                  )
                } else {
                  sessionStore.completeToolCallStep(
                    localAssistantId, toolName, result ?? {},
                  )
                  // 如果是 update_profile 工具，刷新用户资料
                  if (toolName === 'update_profile') {
                    await _refreshProfile()
                  }
                }
                break
              }

              // 任务完成，用完整结果替换流式内容
              case 'task_completed': {
                const content = (event.data.content as string) ?? ''
                const result = event.data.result as Record<string, unknown> | undefined

                // 优先使用 content，其次使用 result，如果都为空则保留已累积的流式内容
                let finalContent: string | null = null
                if (content) {
                  finalContent = content
                } else if (result !== undefined && result !== null) {
                  finalContent = typeof result === 'string' ? result : JSON.stringify(result)
                }

                // 只有当有有效内容时才替换，否则保留已累积的流式内容
                if (finalContent !== null && finalContent !== '') {
                  sessionStore.finalizeAssistantMessage(localAssistantId, finalContent)
                } else {
                  // 只标记为完成，不覆盖内容
                  const msg = sessionStore.messages.find((m) => m.id === localAssistantId)
                  if (msg) msg.streaming = false
                }

                resolve(controller)
                return
              }

              // 任务失败
              case 'task_failed': {
                const error = (event.data.error as string) ?? '执行失败'
                sessionStore.finalizeAssistantMessage(localAssistantId, `⚠️ ${error}`)
                resolve(controller)
                return
              }

              default:
                break
            }
          }
        }

        // SSE 流自然结束，兜底 finalize（防止没有 task_completed 事件时消息卡在 streaming 状态）
        const msg = sessionStore.messages.find((m) => m.id === localAssistantId)
        if (msg && msg.streaming) {
          if (!msg.content) {
            sessionStore.finalizeAssistantMessage(localAssistantId, '抱歉，未能生成回复，请重试。')
          } else {
            msg.streaming = false
          }
        }

        resolve(controller)
      })
      .catch((err) => {
        console.error('[SSE] fetch error:', err.message)
        if (err.name !== 'AbortError') {
          sessionStore.finalizeAssistantMessage(localAssistantId, '连接中断，请重试。')
        }
        resolve(controller)
      })
  })
}

async function _refreshProfile(): Promise<void> {
  const authStore = useAuthStore()
  try {
    await authStore.fetchProfile()
  } catch {
    console.log('[useChat] refresh profile failed')
  }
}

function _parseSSE(chunk: string): SSEEvent | null {
  const lines = chunk.split('\n')
  let eventType = ''
  let dataStr = ''
  for (const line of lines) {
    if (line.startsWith('event:')) eventType = line.slice(6).trim()
    else if (line.startsWith('data:')) dataStr = line.slice(5).trim()
  }
  if (!eventType || !dataStr) return null
  try {
    return { event: eventType as SSEEvent['event'], data: JSON.parse(dataStr) }
  } catch {
    return null
  }
}
