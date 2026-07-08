<script setup lang="ts">
import ContextPickerDialog from '@/components/chat/ContextPickerDialog.vue'
import { useAdvancedSettingsStore } from '@/stores/advancedSettings'
import type { ContextFile } from '@/types'
import { ref } from 'vue'

const advancedSettings = useAdvancedSettingsStore()
const pickerOpen = ref(false)

function addContextFile(file: Omit<ContextFile, 'id'>) {
  advancedSettings.addContextFile(file)
}

function contextTypeLabel(type: ContextFile['type']) {
  if (type === 'branch') return '分支'
  if (type === 'url') return '网址'
  if (type === 'artifact') return '产物'
  return '文件'
}
</script>

<template>
  <div class="context-chips">
    <span v-if="advancedSettings.contextFiles.length === 0" class="context-empty">未添加上下文</span>
    <div
      v-for="chip in advancedSettings.contextFiles"
      :key="chip.id"
      class="context-chip"
      :class="{ active: chip.active }"
      :title="`${chip.label} · ${chip.active ? '点击停用' : '点击激活'}`"
      @click="advancedSettings.toggleContextFile(chip.id)"
    >
      <svg v-if="chip.active" class="chip-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      <span class="chip-type">{{ contextTypeLabel(chip.type) }}</span>
      <span class="chip-label">{{ chip.label }}</span>
      <button class="chip-remove" title="删除上下文" @click.stop="advancedSettings.removeContextFile(chip.id)">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
    <button class="add-chip-btn" title="添加上下文" @click="pickerOpen = true">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
      </svg>
      <span>添加上下文</span>
    </button>
    <ContextPickerDialog v-model="pickerOpen" @add="addContextFile" />
  </div>
</template>

<style scoped lang="scss">
.context-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.context-empty {
  font-size: 12px;
  color: #94a3b8;
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

  &:not(.active) {
    opacity: 0.72;
    text-decoration: line-through;
    text-decoration-color: #cbd5e1;
  }
}

.chip-icon {
  flex-shrink: 0;
}

.chip-type {
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.16);
  font-size: 10px;
}

.chip-label {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: currentColor;
  cursor: pointer;
  opacity: 0.65;

  &:hover {
    background: rgba(15, 23, 42, 0.08);
    opacity: 1;
  }
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
