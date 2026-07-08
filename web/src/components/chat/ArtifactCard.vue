<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAdvancedSettingsStore } from '@/stores/advancedSettings'
import type { Artifact } from '@/types'
import { artifactStageLabel, artifactTypeLabel } from '@/utils/artifacts'

const props = defineProps<{
  artifact: Artifact
}>()

const router = useRouter()
const advancedSettings = useAdvancedSettingsStore()

const deliveryLabel = computed(() => {
  switch (props.artifact.delivery_status) {
    case 'previewed':
      return '已预览'
    case 'delivered':
      return '已交付'
    case 'failed':
      return '交付失败'
    default:
      return '待交付'
  }
})

const deliveryTone = computed(() => {
  switch (props.artifact.delivery_status) {
    case 'delivered':
      return 'delivered'
    case 'failed':
      return 'failed'
    case 'previewed':
      return 'previewed'
    default:
      return 'pending'
  }
})

function openArtifact() {
  router.push(`/artifacts/${props.artifact.id}`)
}

function addAsContext() {
  advancedSettings.addContextFile({
    type: 'artifact',
    value: props.artifact.id,
    label: props.artifact.name,
    active: true,
  })
}
</script>

<template>
  <div class="artifact-card">
    <div class="artifact-card__icon" aria-hidden="true">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="8" y1="13" x2="16" y2="13" />
        <line x1="8" y1="17" x2="14" y2="17" />
      </svg>
    </div>

    <div class="artifact-card__main">
      <div class="artifact-card__title-row">
        <button class="artifact-card__title" @click="openArtifact">
          {{ artifact.name }}
        </button>
        <span class="artifact-card__badge">{{ artifactTypeLabel(artifact.artifact_type) }}</span>
      </div>
      <div class="artifact-card__meta">
        <span>{{ artifactStageLabel(artifact) }}</span>
        <span v-if="artifact.file_type">{{ artifact.file_type }}</span>
        <span class="artifact-card__delivery" :class="`artifact-card__delivery--${deliveryTone}`">
          {{ deliveryLabel }}
        </span>
      </div>
    </div>

    <div class="artifact-card__actions">
      <button class="artifact-card__ghost" @click="addAsContext">加入上下文</button>
      <button class="artifact-card__primary" @click="openArtifact">查看产物</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.artifact-card {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
}

.artifact-card__icon {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: #eff6ff;
  color: #2563eb;
}

.artifact-card__main {
  min-width: 0;
}

.artifact-card__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.artifact-card__title {
  padding: 0;
  border: 0;
  background: transparent;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &:hover { color: #1d4ed8; }
}

.artifact-card__badge {
  flex-shrink: 0;
  padding: 2px 6px;
  border-radius: 5px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 11px;
  font-weight: 700;
}

.artifact-card__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
  color: #64748b;
  font-size: 11px;
}

.artifact-card__delivery {
  padding: 1px 5px;
  border-radius: 5px;
  background: #f1f5f9;
  color: #64748b;
  font-weight: 700;

  &--previewed {
    background: #fffbeb;
    color: #a16207;
  }

  &--delivered {
    background: #ecfdf5;
    color: #047857;
  }

  &--failed {
    background: #fef2f2;
    color: #b91c1c;
  }
}

.artifact-card__actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.artifact-card__ghost,
.artifact-card__primary {
  height: 28px;
  padding: 0 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.artifact-card__ghost {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #475569;

  &:hover {
    border-color: #60a5fa;
    color: #1d4ed8;
  }
}

.artifact-card__primary {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
  font-weight: 700;

  &:hover { background: #1d4ed8; }
}

@media (max-width: 640px) {
  .artifact-card {
    grid-template-columns: 30px minmax(0, 1fr);
  }

  .artifact-card__actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
}
</style>
