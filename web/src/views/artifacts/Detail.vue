<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { artifactsApi } from '@/api/modules/artifacts'
import { useAdvancedSettingsStore } from '@/stores/advancedSettings'
import { useArtifactStore } from '@/stores/artifact'
import { useProjectStore } from '@/stores/project'
import { renderMarkdown } from '@/utils/markdown'
import { artifactStageLabel, artifactTypeLabel } from '@/utils/artifacts'
import type { DeliveryResponse } from '@/types'

const props = defineProps<{
  artifactId: string
}>()

type DeliveryMode = 'local' | 'github' | 'zip'

const router = useRouter()
const artifactStore = useArtifactStore()
const advancedSettings = useAdvancedSettingsStore()
const projectStore = useProjectStore()

const deliveryMode = ref<DeliveryMode>('local')
const selectedMountId = ref('')
const targetPath = ref('')
const githubBaseBranch = ref('main')
const githubTargetBranch = ref('')
const githubPrTitle = ref('')
const githubCommitMessage = ref('')
const deliveryPreview = ref<DeliveryResponse | null>(null)
const deliveryLoading = ref(false)
const deliveryError = ref('')

const artifact = computed(() => artifactStore.currentArtifact)
const isMarkdown = computed(() =>
  !artifact.value?.file_type || artifact.value.file_type === 'markdown'
)
const renderedMarkdown = computed(() =>
  artifact.value ? renderMarkdown(artifact.value.content) : ''
)
const runtimeMetadata = computed(() => metadataObject(artifact.value?.metadata?.runtime))
const runtimeAgent = computed(() => metadataObject(runtimeMetadata.value?.agent_profile))
const runtimeModelRoute = computed(() => metadataObject(runtimeMetadata.value?.model_route))
const runtimeAgentLabel = computed(() =>
  metadataText(runtimeAgent.value, 'name') || metadataText(runtimeAgent.value, 'id')
)
const runtimeModelLabel = computed(() => metadataText(runtimeMetadata.value, 'model_name'))
const runtimeRouteLabel = computed(() =>
  metadataText(runtimeModelRoute.value, 'name') || metadataText(runtimeModelRoute.value, 'route_key')
)
const projectMounts = computed(() => {
  const projectId = artifact.value?.project_id
  return projectId ? projectStore.mountsByProject[projectId] ?? [] : []
})
const connectedLocalMounts = computed(() =>
  projectMounts.value.filter((mount) => mount.mount_type === 'local' && mount.status === 'connected')
)
const connectedGitHubMounts = computed(() =>
  projectMounts.value.filter((mount) => mount.mount_type === 'github' && mount.status === 'connected')
)
const deliveryMounts = computed(() =>
  deliveryMode.value === 'github' ? connectedGitHubMounts.value : connectedLocalMounts.value
)
const selectedGitHubMount = computed(() =>
  connectedGitHubMounts.value.find((mount) => mount.id === selectedMountId.value) ?? null
)
const activeDeliveryReport = computed(() =>
  deliveryPreview.value?.report ?? artifact.value?.delivery_report ?? null
)
const deliveryStatusLabel = computed(() => {
  if (deliveryPreview.value?.status === 'delivered' || artifact.value?.delivery_status === 'delivered') {
    return '已交付'
  }
  if (deliveryPreview.value?.status === 'previewed') {
    return '已预览'
  }
  return '待交付'
})
const canPreviewDelivery = computed(() =>
  Boolean(
    artifact.value
      && (deliveryMode.value === 'zip' || selectedMountId.value)
      && targetPath.value.trim()
      && (deliveryMode.value !== 'github' || githubTargetBranch.value.trim())
      && !deliveryLoading.value
  )
)
const canApplyDelivery = computed(() =>
  Boolean(
    deliveryPreview.value
      && (deliveryMode.value === 'zip' || selectedMountId.value)
      && targetPath.value.trim()
      && (deliveryMode.value !== 'github' || previewBaseSha())
      && !deliveryLoading.value
  )
)
const canExportDelivery = computed(() =>
  artifact.value?.delivery_status === 'delivered' || deliveryPreview.value?.status === 'delivered'
)
const canDownloadZip = computed(() =>
  reportText('delivery_channel') === 'zip' && Boolean(reportText('download_url')) && !deliveryLoading.value
)
const previewButtonLabel = computed(() =>
  deliveryMode.value === 'github'
    ? '预览 PR Diff'
    : deliveryMode.value === 'zip'
      ? '预览 zip'
      : '预览 Diff'
)
const applyButtonLabel = computed(() =>
  deliveryMode.value === 'github'
    ? '创建 PR'
    : deliveryMode.value === 'zip'
      ? '生成 zip'
      : '确认写入'
)

async function loadArtifact() {
  const loaded = await artifactStore.fetchArtifact(props.artifactId)
  await projectStore.fetchProjectMounts(loaded.project_id)
  const channel = artifact.value?.delivery_report?.delivery_channel
  deliveryMode.value = channel === 'github_pr' ? 'github' : channel === 'zip' ? 'zip' : 'local'
  selectedMountId.value = artifact.value?.delivery_report?.mount_id as string
    || deliveryMounts.value[0]?.id
    || ''
  targetPath.value = reportTextFromArtifact('target_path') || artifact.value?.delivery_target_path || artifact.value?.name || ''
  if (deliveryMode.value === 'github') {
    targetPath.value = githubTargetPath(targetPath.value)
  }
  resetGitHubDefaults(true)
  deliveryPreview.value = null
  deliveryError.value = ''
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

async function previewDelivery() {
  if (!artifact.value || !canPreviewDelivery.value) return
  deliveryLoading.value = true
  deliveryError.value = ''
  try {
    const { data } = deliveryMode.value === 'github'
      ? await artifactsApi.previewGitHubDelivery(artifact.value.id, {
          mount_id: selectedMountId.value,
          target_path: targetPath.value.trim(),
          base_branch: githubBaseBranch.value.trim(),
          target_branch: githubTargetBranch.value.trim(),
          pr_title: githubPrTitle.value.trim(),
        })
      : deliveryMode.value === 'zip'
        ? await artifactsApi.previewZipDelivery(artifact.value.id, {
            target_path: targetPath.value.trim(),
          })
        : await artifactsApi.previewDelivery(artifact.value.id, {
          mount_id: selectedMountId.value,
          target_path: targetPath.value.trim(),
        })
    deliveryPreview.value = data
    targetPath.value = data.target_path
  } catch (error) {
    deliveryError.value = deliveryErrorMessage(error)
  } finally {
    deliveryLoading.value = false
  }
}

async function applyDelivery() {
  if (!artifact.value || !canApplyDelivery.value) return
  deliveryLoading.value = true
  deliveryError.value = ''
  try {
    const { data } = deliveryMode.value === 'github'
      ? await artifactsApi.applyGitHubDelivery(artifact.value.id, {
          mount_id: selectedMountId.value,
          target_path: targetPath.value.trim(),
          base_branch: githubBaseBranch.value.trim(),
          target_branch: githubTargetBranch.value.trim(),
          pr_title: githubPrTitle.value.trim(),
          commit_message: githubCommitMessage.value.trim(),
          confirm_write: true,
          expected_base_sha: previewBaseSha() ?? '',
        })
      : deliveryMode.value === 'zip'
        ? await artifactsApi.applyZipDelivery(artifact.value.id, {
            target_path: targetPath.value.trim(),
            confirm_write: true,
          })
        : await artifactsApi.applyDelivery(artifact.value.id, {
          mount_id: selectedMountId.value,
          target_path: targetPath.value.trim(),
          confirm_write: true,
          expected_target_hash: previewTargetHash(),
        })
    deliveryPreview.value = data
    targetPath.value = data.target_path
    await artifactStore.fetchArtifact(artifact.value.id)
  } catch (error) {
    deliveryError.value = deliveryErrorMessage(error)
  } finally {
    deliveryLoading.value = false
  }
}

async function downloadZipPackage() {
  if (!artifact.value || !canDownloadZip.value) return
  deliveryLoading.value = true
  deliveryError.value = ''
  try {
    const { data } = await artifactsApi.downloadZipPackage(artifact.value.id)
    const blob = new Blob([data], { type: 'application/zip' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = reportText('package_name') || `${artifact.value.name}.zip`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    deliveryError.value = deliveryErrorMessage(error)
  } finally {
    deliveryLoading.value = false
  }
}

async function exportDeliveryReport() {
  if (!artifact.value || !canExportDelivery.value) return
  deliveryLoading.value = true
  deliveryError.value = ''
  try {
    const { data } = await artifactsApi.exportDeliveryReport(artifact.value.id)
    const blob = new Blob([data], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${artifact.value.name}.delivery.md`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    deliveryError.value = deliveryErrorMessage(error)
  } finally {
    deliveryLoading.value = false
  }
}

function deliveryErrorMessage(error: unknown) {
  const maybeError = error as { response?: { data?: { detail?: string } } }
  return maybeError.response?.data?.detail ?? '交付失败'
}

function previewTargetHash(): string | null | undefined {
  const fingerprint = deliveryPreview.value?.report?.target_fingerprint
  if (!fingerprint || typeof fingerprint !== 'object') {
    return undefined
  }
  const hash = (fingerprint as { sha256?: unknown }).sha256
  return typeof hash === 'string' || hash === null ? hash : undefined
}

function previewBaseSha(): string | undefined {
  const baseSha = deliveryPreview.value?.report?.base_sha
  return typeof baseSha === 'string' && baseSha ? baseSha : undefined
}

function reportText(key: string): string {
  const value = activeDeliveryReport.value?.[key]
  if (typeof value === 'string' || typeof value === 'number') {
    return String(value)
  }
  return ''
}

function reportTextFromArtifact(key: string): string {
  const value = artifact.value?.delivery_report?.[key]
  if (typeof value === 'string' || typeof value === 'number') {
    return String(value)
  }
  return ''
}

function metadataObject(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function metadataText(record: Record<string, unknown> | null, key: string): string {
  const value = record?.[key]
  return typeof value === 'string' && value.trim() ? value : ''
}

function selectDeliveryMode(mode: DeliveryMode) {
  if (deliveryMode.value === mode) return
  deliveryMode.value = mode
}

function resetSelectedMountForMode() {
  selectedMountId.value = deliveryMode.value === 'zip' ? '' : deliveryMounts.value[0]?.id || ''
  deliveryPreview.value = null
  deliveryError.value = ''
  resetGitHubDefaults(true)
}

function resetGitHubDefaults(force = false) {
  if (!artifact.value) return
  const defaultBranch = selectedGitHubMount.value?.metadata?.default_branch
  githubBaseBranch.value = typeof defaultBranch === 'string' && defaultBranch ? defaultBranch : 'main'
  if (force || !githubTargetBranch.value) {
    githubTargetBranch.value = `agentforge/${artifact.value.id.slice(0, 8)}`
  }
  if (force || !githubPrTitle.value) {
    githubPrTitle.value = `Deliver ${artifact.value.name}`
  }
  if (force || !githubCommitMessage.value) {
    githubCommitMessage.value = `Deliver ${artifact.value.name}`
  }
}

function githubTargetPath(value: string): string {
  return value.startsWith('github://') ? value.split('/').slice(4).join('/') : value
}

onMounted(loadArtifact)

watch(
  () => props.artifactId,
  () => {
    void loadArtifact()
  },
)

watch(deliveryMode, resetSelectedMountForMode)

watch(selectedMountId, () => {
  if (deliveryMode.value === 'github') {
    deliveryPreview.value = null
    resetGitHubDefaults()
  }
})
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
        <span v-if="runtimeAgentLabel">Agent {{ runtimeAgentLabel }}</span>
        <span v-if="runtimeModelLabel">模型 {{ runtimeModelLabel }}</span>
        <span v-if="runtimeRouteLabel">路由 {{ runtimeRouteLabel }}</span>
      </div>

      <section class="artifact-viewer__delivery">
        <div class="artifact-viewer__delivery-header">
          <h2>交付写回</h2>
          <span :class="['artifact-viewer__delivery-status', `is-${deliveryPreview?.status ?? artifact.delivery_status}`]">
            {{ deliveryStatusLabel }}
          </span>
        </div>

        <div class="artifact-viewer__delivery-mode" role="tablist" aria-label="交付方式">
          <button
            :class="{ 'is-active': deliveryMode === 'local' }"
            :disabled="deliveryLoading || connectedLocalMounts.length === 0"
            type="button"
            @click="selectDeliveryMode('local')"
          >
            本地写回
          </button>
          <button
            :class="{ 'is-active': deliveryMode === 'github' }"
            :disabled="deliveryLoading || connectedGitHubMounts.length === 0"
            type="button"
            @click="selectDeliveryMode('github')"
          >
            GitHub PR
          </button>
          <button
            :class="{ 'is-active': deliveryMode === 'zip' }"
            :disabled="deliveryLoading"
            type="button"
            @click="selectDeliveryMode('zip')"
          >
            zip 包
          </button>
        </div>

        <div class="artifact-viewer__delivery-form">
          <label
            v-if="deliveryMode !== 'zip'"
            class="artifact-viewer__field"
            for="delivery-mount"
          >
            <span>目标代码库</span>
            <select
              id="delivery-mount"
              v-model="selectedMountId"
              :disabled="deliveryLoading || deliveryMounts.length === 0"
            >
              <option value="" disabled>选择代码库</option>
              <option
                v-for="mount in deliveryMounts"
                :key="mount.id"
                :value="mount.id"
              >
                {{ mount.display_name }}
              </option>
            </select>
          </label>

          <label class="artifact-viewer__field" for="delivery-target-path">
            <span>写入路径</span>
            <input
              id="delivery-target-path"
              v-model="targetPath"
              type="text"
              :disabled="deliveryLoading"
              placeholder="src/main.py"
            >
          </label>

          <label
            v-if="deliveryMode === 'github'"
            class="artifact-viewer__field"
            for="github-base-branch"
          >
            <span>Base</span>
            <input
              id="github-base-branch"
              v-model="githubBaseBranch"
              type="text"
              :disabled="deliveryLoading"
              placeholder="main"
            >
          </label>

          <label
            v-if="deliveryMode === 'github'"
            class="artifact-viewer__field"
            for="github-target-branch"
          >
            <span>交付分支</span>
            <input
              id="github-target-branch"
              v-model="githubTargetBranch"
              type="text"
              :disabled="deliveryLoading"
              placeholder="agentforge/task"
            >
          </label>

          <label
            v-if="deliveryMode === 'github'"
            class="artifact-viewer__field artifact-viewer__field--wide"
            for="github-pr-title"
          >
            <span>PR 标题</span>
            <input
              id="github-pr-title"
              v-model="githubPrTitle"
              type="text"
              :disabled="deliveryLoading"
              placeholder="Deliver artifact"
            >
          </label>

          <div class="artifact-viewer__delivery-actions">
            <button
              class="artifact-viewer__secondary"
              :disabled="!canPreviewDelivery"
              @click="previewDelivery"
            >
              {{ previewButtonLabel }}
            </button>
            <button
              class="artifact-viewer__danger"
              :disabled="!canApplyDelivery"
              @click="applyDelivery"
            >
              {{ applyButtonLabel }}
            </button>
            <button
              class="artifact-viewer__secondary"
              :disabled="!canExportDelivery || deliveryLoading"
              @click="exportDeliveryReport"
            >
              导出报告
            </button>
            <button
              v-if="reportText('delivery_channel') === 'zip'"
              class="artifact-viewer__secondary"
              :disabled="!canDownloadZip"
              @click="downloadZipPackage"
            >
              下载 zip
            </button>
          </div>
        </div>

        <p v-if="deliveryError" class="artifact-viewer__delivery-error">
          {{ deliveryError }}
        </p>

        <pre
          v-if="deliveryPreview?.unified_diff"
          class="artifact-viewer__diff"
        ><code>{{ deliveryPreview.unified_diff }}</code></pre>

        <div
          v-if="activeDeliveryReport"
          class="artifact-viewer__delivery-report"
        >
          <span v-if="reportText('target_path')">目标：{{ reportText('target_path') }}</span>
          <span v-if="reportText('repo_full_name')">仓库：{{ reportText('repo_full_name') }}</span>
          <span v-if="reportText('base_branch')">Base：{{ reportText('base_branch') }}</span>
          <span v-if="reportText('target_branch')">分支：{{ reportText('target_branch') }}</span>
          <span v-if="reportText('backup_path')">备份：{{ reportText('backup_path') }}</span>
          <span v-if="reportText('bytes_written')">写入：{{ reportText('bytes_written') }} bytes</span>
          <span v-if="reportText('package_name')">包：{{ reportText('package_name') }}</span>
          <span v-if="reportText('file_count')">文件：{{ reportText('file_count') }}</span>
          <span v-if="reportText('package_sha256')">SHA256：{{ reportText('package_sha256') }}</span>
          <a
            v-if="reportText('pr_url')"
            :href="reportText('pr_url')"
            target="_blank"
            rel="noreferrer"
          >
            PR：{{ reportText('pr_url') }}
          </a>
          <span v-if="reportText('commit_sha')">Commit：{{ reportText('commit_sha') }}</span>
        </div>
      </section>

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

.artifact-viewer__delivery {
  margin-bottom: 22px;
  padding: 16px;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #f8fafc;
}

.artifact-viewer__delivery-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;

  h2 {
    margin: 0;
    color: #0f172a;
    font-size: 15px;
    font-weight: 750;
    line-height: 1.3;
  }
}

.artifact-viewer__delivery-status {
  padding: 3px 8px;
  border-radius: 6px;
  background: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 700;

  &.is-delivered {
    background: #dcfce7;
    color: #166534;
  }

  &.is-previewed {
    background: #dbeafe;
    color: #1d4ed8;
  }
}

.artifact-viewer__delivery-mode {
  display: inline-flex;
  gap: 2px;
  margin-bottom: 12px;
  padding: 3px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #e2e8f0;

  button {
    height: 28px;
    padding: 0 10px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: #475569;
    font-size: 12px;
    font-weight: 750;
    cursor: pointer;

    &.is-active {
      background: #fff;
      color: #0f172a;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    }

    &:disabled {
      cursor: not-allowed;
      opacity: 0.48;
    }
  }
}

.artifact-viewer__delivery-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: end;
  gap: 12px;
}

.artifact-viewer__field {
  display: grid;
  gap: 6px;
  min-width: 0;

  span {
    color: #475569;
    font-size: 12px;
    font-weight: 700;
  }

  select,
  input {
    width: 100%;
    height: 34px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    background: #fff;
    color: #0f172a;
    font-size: 13px;
    outline: none;
  }

  select {
    padding: 0 30px 0 10px;
  }

  input {
    padding: 0 10px;
  }

  select:focus,
  input:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
  }
}

.artifact-viewer__field--wide {
  grid-column: span 2;
}

.artifact-viewer__delivery-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.artifact-viewer__secondary,
.artifact-viewer__danger {
  height: 34px;
  padding: 0 12px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;

  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
}

.artifact-viewer__secondary {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;

  &:hover:not(:disabled) {
    border-color: #93c5fd;
    color: #1d4ed8;
  }
}

.artifact-viewer__danger {
  border: 1px solid #b91c1c;
  background: #b91c1c;
  color: #fff;

  &:hover:not(:disabled) {
    background: #991b1b;
  }
}

.artifact-viewer__delivery-error {
  margin: 12px 0 0;
  color: #b91c1c;
  font-size: 13px;
  font-weight: 700;
}

.artifact-viewer__diff {
  margin: 14px 0 0;
  max-height: 360px;
  padding: 12px;
  overflow: auto;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #111827;
  color: #e5e7eb;
  font-size: 12px;
  line-height: 1.6;
}

.artifact-viewer__delivery-report {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;

  span,
  a {
    padding: 3px 8px;
    border-radius: 6px;
    background: #fff;
    color: #475569;
    font-size: 12px;
    font-weight: 650;
    text-decoration: none;
  }

  a {
    color: #1d4ed8;

    &:hover {
      text-decoration: underline;
    }
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

  .artifact-viewer__delivery-form {
    grid-template-columns: 1fr;
  }

  .artifact-viewer__field--wide {
    grid-column: auto;
  }

  .artifact-viewer__delivery-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
