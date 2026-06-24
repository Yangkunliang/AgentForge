<script setup lang="ts">
import { ref } from 'vue'

interface ContextChip {
  label: string
  active: boolean
}

const chips = ref<ContextChip[]>([
  { label: 'main 分支', active: true },
  { label: 'PRD-CLAW.md', active: true },
  { label: 'engine.py', active: false },
])

function toggleChip(index: number) {
  chips.value[index].active = !chips.value[index].active
}
</script>

<template>
  <div class="context-chips">
    <div
      v-for="(chip, index) in chips"
      :key="chip.label"
      class="context-chip"
      :class="{ active: chip.active }"
      @click="toggleChip(index)"
    >
      <svg v-if="chip.active" class="chip-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      <span class="chip-label">{{ chip.label }}</span>
    </div>
    <button class="add-chip-btn" title="添加上下文">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
      </svg>
      <span>+ 添加上下文</span>
    </button>
  </div>
</template>

<style scoped lang="scss">
.context-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.context-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #f3f4f6;
  border-radius: 16px;
  font-size: 12px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;

  &:hover { background: #e5e7eb; }

  &.active {
    background: #eff6ff;
    color: #2563eb;
    border: 1px solid #bfdbfe;
  }
}

.chip-icon {
  flex-shrink: 0;
}

.add-chip-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: transparent;
  border: 1px dashed #d1d5db;
  border-radius: 16px;
  font-size: 12px;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: #409eff;
    color: #409eff;
    background: #f0f7ff;
  }
}
</style>
