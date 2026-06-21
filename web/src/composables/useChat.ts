/**
 * useChat — 封装「发消息 → 订阅 SSE → 流式更新气泡」完整流程
 *
 * 多 Agent 的执行细节对用户透明：
 * - 用户只看到"AI 思考中..." → 文字逐步出现 → 完成
 * - task_started / bid_received / agent_assigned 等内部事件静默忽略
 * - 只有 llm_response（流式片段）和 task_completed（最终结果）影响 UI
 */
import { ref } from 'vue'
import { sessionsApi } from '@/api/modules/sessions'
import { useSessionStore } from '@/stores/session'
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
              // 流式文字片段（LLM 逐 token 输出）
              case 'llm_response': {
                const delta = (event.data.delta as string) ?? ''
                sessionStore.appendStreamChunk(localAssistantId, delta)
                break
              }

              // 任务完成，用完整结果替换流式内容
              case 'task_completed': {
                const content = (event.data.content as string) ?? ''
                if (content) {
                  sessionStore.finalizeAssistantMessage(localAssistantId, content)
                } else {
                  const result = event.data.result as Record<string, unknown> | undefined
                  sessionStore.finalizeAssistantMessage(
                    localAssistantId,
                    typeof result === 'string' ? result : JSON.stringify(result ?? ''),
                  )
                }
                // 不 abort，直接 break 出循环，让流自然关闭
                resolve(controller)
                return  // 跳出整个循环
              }

              // 任务失败
              case 'task_failed': {
                const error = (event.data.error as string) ?? '执行失败'
                sessionStore.finalizeAssistantMessage(localAssistantId, `⚠️ ${error}`)
                resolve(controller)
                return  // 跳出整个循环
              }

              // heartbeat / 内部事件：静默忽略，不影响 UI
              default:
                break
            }
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
