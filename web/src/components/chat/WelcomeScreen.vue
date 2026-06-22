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
    icon: '✏️',
    title: '给我起个昵称',
    desc: '让 AI 帮你取一个个性的显示昵称',
    prompt: '帮我想一个好听的昵称，结合我的职业（全栈开发者）和个性，给我 5 个选择，每个简短说明一下风格，然后问我选哪个，选好后帮我直接设置上去。',
    color: '#eff6ff',
  },
  {
    icon: '🎨',
    title: '换个 AI 头像',
    desc: '给 AI 助手换一个你喜欢的风格',
    prompt: '我想给你（AI）换个头像，告诉我你支持哪些风格，然后引导我上传或选择一张图片。',
    color: '#fdf4ff',
  },
  {
    icon: '🤖',
    title: '给 AI 起个名字',
    desc: '为你的专属 AI 助手取一个昵称',
    prompt: '我想给你这个 AI 助手起一个专属名字，你帮我想几个有科技感又亲切的名字推荐给我，我会从中选一个作为你的称呼。',
    color: '#fff7ed',
  },
  {
    icon: '🐛',
    title: '帮我 Debug',
    desc: '粘贴错误信息或代码，AI 秒速定位问题',
    prompt: '帮我 debug，我来粘贴代码和报错信息：\n\n```\n// 粘贴你的代码或错误堆栈\n```',
    color: '#f0fdf4',
  },
  {
    icon: '🏗️',
    title: '系统设计',
    desc: '描述你的需求，AI 给出架构方案',
    prompt: '我需要设计一个系统，请根据我的描述给出架构方案（技术选型、模块划分、数据流）：\n\n【我的需求】：',
    color: '#fefce8',
  },
  {
    icon: '📝',
    title: '代码 Review',
    desc: 'AI 帮你找潜在问题和优化点',
    prompt: '请帮我做 Code Review，从可读性、性能、安全性三个维度分析，并给出改进建议：\n\n```\n// 粘贴你的代码\n```',
    color: '#f0f9ff',
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
      <span class="headline-star">✶</span>
      <h2>有什么可以帮你的？</h2>
      <p class="headline-sub">点击下面的卡片快速开始，或直接输入你的问题</p>
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
        <svg class="card-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
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

.headline-star {
  font-size: 32px;
  color: #409eff;
  line-height: 1;
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
