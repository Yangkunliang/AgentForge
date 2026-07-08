<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AssistantMessage from '@/components/chat/AssistantMessage.vue'
import type { ChatMessage } from '@/types'

const route = useRoute()

const now = '2026-07-07T09:00:00.000Z'

const messages: Record<string, ChatMessage> = {
  pure: {
    id: 'e2e-pure-dialogue',
    role: 'assistant',
    content: '这是一个普通回复，没有工具调用。',
    created_at: now,
    streaming: false,
  },
  mixed: {
    id: 'e2e-mixed-steps',
    role: 'assistant',
    content: '已完成查询和代码执行，下面是结果摘要。',
    created_at: now,
    streaming: false,
    execution_steps: [
      {
        type: 'thinking',
        content: '分析用户意图，先查询天气，再执行一段代码。',
        streaming: false,
        duration_ms: 86,
      },
      {
        type: 'tool_call',
        tool_name: 'get_weather',
        arguments: { city: '厦门' },
        status: 'completed',
        result: { temperature: 27, unit: 'C', description: '多云' },
        duration_ms: 138,
      },
      {
        type: 'code_execution',
        code: "print('hello from code')",
        status: 'completed',
        stdout: 'hello from code\n',
        stderr: '',
        exit_code: 0,
        duration_ms: 42,
      },
    ],
  },
  legacy: {
    id: 'e2e-legacy-tool-calls',
    role: 'assistant',
    content: '这是历史消息，只有旧版 tool_calls 字段。',
    created_at: now,
    streaming: false,
    tool_calls: [
      {
        tool_name: 'web_search',
        arguments: { query: 'AgentForge' },
        status: 'completed',
        result: { count: 3 },
      },
    ],
  },
  interrupted: {
    id: 'e2e-interrupted-stream',
    role: 'assistant',
    content: '连接中断，请重试。',
    created_at: now,
    streaming: false,
  },
  streaming: {
    id: 'e2e-streaming-steps',
    role: 'assistant',
    content: '',
    created_at: now,
    streaming: true,
    execution_steps: [
      {
        type: 'thinking',
        content: '正在判断下一步需要调用哪个工具。',
        streaming: false,
        duration_ms: 64,
      },
      {
        type: 'tool_call',
        tool_name: 'get_weather',
        arguments: { city: '厦门' },
        status: 'running',
      },
    ],
  },
}

const scenario = computed(() => String(route.query.scenario ?? 'mixed'))
const message = computed(() => messages[scenario.value] ?? messages.mixed)
</script>

<template>
  <main class="e2e-execution-steps-page">
    <section class="e2e-execution-steps-shell">
      <AssistantMessage :message="message" agent-name="CodeSoul" />
    </section>
  </main>
</template>

<style scoped lang="scss">
.e2e-execution-steps-page {
  min-height: 100vh;
  padding: 24px;
  background: #ffffff;
}

.e2e-execution-steps-shell {
  max-width: 760px;
  margin: 0 auto;
}

@media (max-width: 480px) {
  .e2e-execution-steps-page {
    padding: 12px;
  }
}
</style>
