<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAdvancedSettingsStore } from '@/stores/advancedSettings'
import { useArtifactStore } from '@/stores/artifact'
import { renderMarkdown } from '@/utils/markdown'
import { artifactStageLabel, artifactTypeLabel } from '@/utils/artifacts'

const props = defineProps<{
  artifactId: string
}>()

const router = useRouter()
const artifactStore = useArtifactStore()
const advancedSettings = useAdvancedSettingsStore()

const artifact = computed(() => artifactStore.currentArtifact)
const isMarkdown = computed(() =>
  !artifact.value?.file_type || artifact.value.file_type === 'markdown'
)
const renderedMarkdown = computed(() =>
  artifact.value ? renderMarkdown(artifact.value.content) : ''
)

async function loadArtifact() {
  await artifactStore.fetchArtifact(props.artifactId)
}

function addAsContext() {
  if (!artifact.value) return
  advancedSettings.addContextFile({
    type: 'artifact',
    value: artifact.value.id,
    label: artifact.value.name,
    active: true,
  })
}

onMounted(loadArtifact)

watch(
  () => props.artifactId,
  () => {
    void loadArtifact()
  },
)
</script>

<template>
  <div class="artifact-viewer">
    <div class="artifact-viewer__header">
      <button class="artifact-viewer__back" title="返回" @click="router.back()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12" />
          <polyline points="12 19 5 12 12 5" />
        </svg>
      </button>

      <div class="artifact-viewer__title-group">
        <div class="artifact-viewer__eyebrow" v-if="artifact">
          <span>{{ artifactTypeLabel(artifact.artifact_type) }}</span>
          <span>{{ artifactStageLabel(artifact) }}</span>
        </div>
        <h1 class="artifact-viewer__title">
          {{ artifact?.name ?? '产物详情' }}
        </h1>
      </div>

      <button
        class="artifact-viewer__context"
        :disabled="!artifact"
        @click="addAsContext"
      >
        加入上下文
      </button>
    </div>

    <div v-if="artifactStore.loading && !artifact" class="artifact-viewer__state">
      正在加载产物
    </div>

    <div v-else-if="artifact" class="artifact-viewer__body">
      <div class="artifact-viewer__meta">
        <span>{{ artifact.file_type ?? 'markdown' }}</span>
        <span v-if="artifact.pipeline_run_id">Pipeline {{ artifact.pipeline_run_id.slice(0, 8) }}</span>
        <span v-if="artifact.session_id">Session {{ artifact.session_id.slice(0, 8) }}</span>
      </div>

      <article
        v-if="isMarkdown"
        class="markdown-body"
        v-html="renderedMarkdown"
      />
      <pre v-else class="artifact-viewer__pre"><code>{{ artifact.content }}</code></pre>
    </div>
  </div>
</template>

<style scoped lang="scss">
.artifact-viewer {
  min-height: 100%;
  padding: 28px;
  background: #fff;
}

.artifact-viewer__header {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  max-width: 980px;
  margin: 0 auto 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.artifact-viewer__back {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #fff;
  color: #475569;
  cursor: pointer;

  &:hover {
    border-color: #93c5fd;
    color: #1d4ed8;
    background: #eff6ff;
  }
}

.artifact-viewer__title-group {
  min-width: 0;
}

.artifact-viewer__eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.artifact-viewer__title {
  margin: 0;
  color: #0f172a;
  font-size: 22px;
  font-weight: 750;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.artifact-viewer__context {
  height: 34px;
  padding: 0 14px;
  border: 1px solid #2563eb;
  border-radius: 7px;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;

  &:hover { background: #1d4ed8; }
  &:disabled {
    border-color: #cbd5e1;
    background: #e2e8f0;
    color: #94a3b8;
    cursor: not-allowed;
  }
}

.artifact-viewer__state,
.artifact-viewer__body {
  max-width: 980px;
  margin: 0 auto;
}

.artifact-viewer__state {
  padding: 64px 0;
  color: #94a3b8;
  text-align: center;
}

.artifact-viewer__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;

  span {
    padding: 3px 8px;
    border-radius: 6px;
    background: #f1f5f9;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
  }
}

.markdown-body {
  color: #1f2937;
  font-size: 14px;
  line-height: 1.8;
}

.artifact-viewer__pre {
  margin: 0;
  padding: 16px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.7;
}

@media (max-width: 720px) {
  .artifact-viewer {
    padding: 18px;
  }

  .artifact-viewer__header {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .artifact-viewer__context {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
