<script setup lang="ts">
/**
 * UserAvatar — 通用头像组件
 *
 * 支持：
 *   - 图片头像（avatarUrl）
 *   - 文字头像（取 name 首字，自动配色）
 *
 * Props:
 *   name        显示名称（用于生成文字+颜色）
 *   avatarUrl   可选，有则展示图片
 *   size        头像尺寸 px，默认 32
 *   shape       'circle' | 'squircle'，默认 circle
 */

import { computed } from 'vue'

const props = withDefaults(defineProps<{
  name: string
  avatarUrl?: string
  size?: number
  shape?: 'circle' | 'squircle'
}>(), {
  size: 32,
  shape: 'circle',
})

// ── 取名字首字 ──────────────────────────────────────────────
const initial = computed(() => {
  const s = props.name?.trim()
  if (!s) return '?'
  // 中文直接取第一个字
  if (/[\u4e00-\u9fa5]/.test(s[0])) return s[0]
  // 英文取大写首字母
  return s[0].toUpperCase()
})

// ── 根据名称生成稳定颜色（哈希） ────────────────────────────
const PALETTE = [
  ['#6366f1', '#818cf8'],  // indigo
  ['#8b5cf6', '#a78bfa'],  // violet
  ['#0ea5e9', '#38bdf8'],  // sky
  ['#10b981', '#34d399'],  // emerald
  ['#f59e0b', '#fbbf24'],  // amber
  ['#ef4444', '#f87171'],  // red
  ['#ec4899', '#f472b6'],  // pink
  ['#14b8a6', '#2dd4bf'],  // teal
  ['#f97316', '#fb923c'],  // orange
  ['#64748b', '#94a3b8'],  // slate
]

function hashName(name: string): number {
  let h = 0
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) >>> 0
  }
  return h
}

const colors = computed(() => {
  const idx = hashName(props.name || '') % PALETTE.length
  return PALETTE[idx]
})

// ── 样式 ─────────────────────────────────────────────────────
const borderRadius = computed(() =>
  props.shape === 'squircle' ? `${props.size * 0.28}px` : '50%'
)

const fontSize = computed(() => {
  // 中文字符用稍小一点的比例
  const isCJK = /[\u4e00-\u9fa5]/.test(initial.value)
  return `${Math.round(props.size * (isCJK ? 0.46 : 0.42))}px`
})
</script>

<template>
  <div class="user-avatar" :style="{
    width: `${size}px`,
    height: `${size}px`,
    borderRadius,
    background: avatarUrl ? 'transparent' : `linear-gradient(135deg, ${colors[0]}, ${colors[1]})`,
    fontSize,
  }">
    <img v-if="avatarUrl" :src="avatarUrl" :alt="name" class="avatar-img" />
    <span v-else class="avatar-text">{{ initial }}</span>
  </div>
</template>

<style scoped lang="scss">
.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
  user-select: none;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-text {
  color: #fff;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0;
}
</style>
