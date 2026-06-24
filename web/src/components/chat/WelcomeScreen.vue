<script setup lang="ts">
/**
 * WelcomeScreen — 欢迎页
 *
 * 功能：
 * 1. 个性化问候（时段 + 昵称）
 * 2. 快捷功能引导卡，点击将话术填入输入框
 *
 * Emits:
 *   prompt(text) — 用户点击引导卡，父组件把 text 填入输入框
 */

import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import UserAvatar from '@/components/common/UserAvatar.vue'

const authStore = useAuthStore()

const emit = defineEmits<{ prompt: [text: string] }>()

// ── 时段问候 ─────────────────────────────────────────────────
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6)  return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  if (h < 22) return '晚上好'
  return '夜深了'
})

const displayName = computed(() => authStore.displayName)
const avatarUrl = computed(() => authStore.avatarUrl)

// ── 引导卡片 ─────────────────────────────────────────────────
interface PromptCard {
  icon: string
  title: string
  desc: string
  prompt: string
  color: string   // 图标背景色
}

const cards: PromptCard[] = [
  {
    icon: '🐛',
    title: '帮我 Debug',
    desc: '粘贴报错信息，AI 秒速定位根因',
    prompt: '帮我 debug，我来粘贴代码和报错信息：\n\n```\n// 粘贴你的代码或错误堆栈\n```',
    color: '#f0fdf4',
  },
  {
    icon: '✨',
    title: '新功能开发',
    desc: '描述需求，AI 拆解任务到可执行代码',
    prompt: '我需要开发一个新功能，请帮我分析需求、拆解任务并生成代码：\n\n【功能描述】：',
    color: '#eff6ff',
  },
  {
    icon: '🔄',
    title: '迭代优化',
    desc: '改现有功能，AI 分析影响范围再动手',
    prompt: '我需要对现有功能做迭代优化，请先分析改动范围和影响点，再给出实现方案：\n\n【要改的内容】：',
    color: '#f0f9ff',
  },
  {
    icon: '🎨',
    title: 'UI / 交互调整',
    desc: '描述或上传设计稿，直接生成组件代码',
    prompt: '我需要调整 UI 或交互，请帮我生成对应的前端组件代码：\n\n【调整描述】：',
    color: '#fdf4ff',
  },
  {
    icon: '🏗️',
    title: '架构 & 技术选型',
    desc: '描述系统需求，AI 给出架构方案',
    prompt: '我需要设计一个系统，请给出架构方案（技术选型、模块划分、数据流）：\n\n【系统需求】：',
    color: '#fefce8',
  },
  {
    icon: '📝',
    title: '代码 Review',
    desc: '从可读性、性能、安全性三个维度分析',
    prompt: '请帮我做 Code Review，从可读性、性能、安全性三个维度分析，并给出具体改进建议：\n\n```\n// 粘贴你的代码\n```',
    color: '#fff7ed',
  },
]
</script>

<template>
  <div class="welcome-screen">

    <!-- 顶部问候 -->
    <div class="greeting-row">
      <UserAvatar
        :name="displayName"
        :avatar-url="avatarUrl"
        :size="52"
        shape="circle"
        class="greeting-avatar"
      />
      <div class="greeting-text">
        <p class="greeting-sub">{{ greeting }}，</p>
        <h1 class="greeting-name">{{ displayName }} 👋</h1>
      </div>
    </div>

    <!-- 主问语 -->
    <div class="headline">
      <div class="headline-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
        </svg>
      </div>
      <h2>有什么可以帮你的？</h2>
      <p class="headline-sub">点击卡片快速开始，或直接描述你的需求</p>
    </div>

    <!-- 引导卡片网格 -->
    <div class="cards-grid">
      <button
        v-for="card in cards"
        :key="card.title"
        class="prompt-card"
        @click="emit('prompt', card.prompt)"
      >
        <span class="card-icon" :style="{ background: card.color }">{{ card.icon }}</span>
        <div class="card-body">
          <span class="card-title">{{ card.title }}</span>
          <span class="card-desc">{{ card.desc }}</span>
        </div>
        <svg class="card-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
        </svg>
      </button>
    </div>

  </div>
</template>

<style scoped lang="scss">
.welcome-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px 24px;
  gap: 32px;
  max-width: 720px;
  margin: 0 auto;
  width: 100%;
}

// ── 问候区 ────────────────────────────────────────────────────
.greeting-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.greeting-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.greeting-sub {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
  line-height: 1;
}

.greeting-name {
  font-size: 26px;
  font-weight: 700;
  color: #111827;
  margin: 0;
  line-height: 1.2;
}

// ── 标题区 ────────────────────────────────────────────────────
.headline {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.headline-icon {
  width: 40px;
  height: 40px;
  background: #eff6ff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  margin-bottom: 2px;
}

h2 {
  font-size: 20px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.headline-sub {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}

// ── 卡片网格 ──────────────────────────────────────────────────
.cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  width: 100%;
}

.prompt-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.1s;

  &:hover {
    border-color: #409eff;
    box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
    transform: translateY(-1px);

    .card-arrow { opacity: 1; transform: translateX(2px); }
  }

  &:active { transform: translateY(0); }
}

.card-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-desc {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-arrow {
  color: #9ca3af;
  opacity: 0;
  flex-shrink: 0;
  transition: opacity 0.15s, transform 0.15s;
}

// ── 移动端 ────────────────────────────────────────────────────
@media (max-width: 768px) {
  .welcome-screen {
    padding: 24px 16px 16px;
    gap: 24px;
  }

  .greeting-name { font-size: 22px; }
  .greeting-avatar { width: 44px !important; height: 44px !important; }

  .cards-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .card-arrow { opacity: 1; }  // 移动端常显
}
</style>
