import { ref, onUnmounted } from 'vue'
import { useTaskStore } from '@/stores/task'
import type { SSEEvent, SSEEventType } from '@/types'

interface UseSSEOptions {
  maxRetries?: number
  maxRetryDelay?: number
  onEvent?: (event: SSEEvent) => void
  onError?: (error: Error) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export function useSSE(taskId: string, options: UseSSEOptions = {}) {
  const {
    maxRetries = 5,
    maxRetryDelay = 30000,
    onEvent,
    onError,
    onConnect,
    onDisconnect,
  } = options

  const taskStore = useTaskStore()
  const connected = ref(false)
  const retryCount = ref(0)

  let abortController: AbortController | null = null
  let retryTimeout: ReturnType<typeof setTimeout> | null = null

  function parseSSEMessage(chunk: string): SSEEvent | null {
    const lines = chunk.split('\n')
    let eventType: SSEEventType | null = null
    let dataStr = ''

    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim() as SSEEventType
      } else if (line.startsWith('data:')) {
        dataStr = line.slice(5).trim()
      }
    }

    if (eventType && dataStr) {
      try {
        const data = JSON.parse(dataStr)
        return { event: eventType, data }
      } catch {
        return null
      }
    }
    return null
  }

  async function connect() {
    abortController = new AbortController()

    const token = localStorage.getItem('access_token')
    if (!token) {
      onError?.(new Error('No authentication token'))
      return
    }

    try {
      const response = await fetch(`/api/v1/tasks/${taskId}/stream`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        signal: abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      connected.value = true
      retryCount.value = 0
      onConnect?.()

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() ?? ''

        for (const chunk of lines) {
          const event = parseSSEMessage(chunk)
          if (event) {
            taskStore.handleSSEEvent(event)
            onEvent?.(event)
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // 主动关闭，不重连
        return
      }

      connected.value = false
      onError?.(error as Error)

      // 指数退避重连
      if (retryCount.value < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryCount.value), maxRetryDelay)
        retryCount.value++
        retryTimeout = setTimeout(connect, delay)
      }
    } finally {
      connected.value = false
      onDisconnect?.()
    }
  }

  function disconnect() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    if (retryTimeout) {
      clearTimeout(retryTimeout)
      retryTimeout = null
    }
    connected.value = false
    taskStore.clearEvents()
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    retryCount,
    connect,
    disconnect,
  }
}
