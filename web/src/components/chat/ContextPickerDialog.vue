<script setup lang="ts">
import { projectsApi } from '@/api/modules/projects'
import { useProjectStore } from '@/stores/project'
import { computed, ref, watch } from 'vue'
import type { ContextFile, ContextFileType, MountFileEntry } from '@/types'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'add', value: Omit<ContextFile, 'id'>): void
}>()

const projectStore = useProjectStore()
const currentType = ref<ContextFileType>('file')
const value = ref('')
const label = ref('')
const activeMountId = ref('')
const selectedMountId = ref<string | undefined>()
const currentPath = ref('')
const entries = ref<MountFileEntry[]>([])
const loadingFiles = ref(false)
const fileError = ref('')
const contextTypes: ContextFileType[] = ['file', 'branch', 'url']

const connectedLocalMounts = computed(() => {
  const projectId = projectStore.currentProjectId
  if (!projectId) return []
  return (projectStore.mountsByProject[projectId] ?? []).filter(
    (mount) => mount.mount_type === 'local' && mount.status === 'connected',
  )
})

const activeMount = computed(() =>
  connectedLocalMounts.value.find((mount) => mount.id === activeMountId.value) ?? null
)

const title = computed(() => {
  if (currentType.value === 'branch') return '添加分支'
  if (currentType.value === 'url') return '添加网址'
  return '添加文件'
})

const placeholder = computed(() => {
  if (currentType.value === 'branch') return 'main'
  if (currentType.value === 'url') return 'https://example.com/spec'
  return 'src/api/routes/sessions.py'
})

const canSubmit = computed(() => {
  const trimmed = value.value.trim()
  if (!trimmed) return false
  if (currentType.value !== 'url') return true
  try {
    const url = new URL(trimmed)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
})

function close() {
  emit('update:modelValue', false)
}

function submit() {
  if (!canSubmit.value) return
  emit('add', {
    type: currentType.value,
    value: value.value.trim(),
    label: label.value.trim() || value.value.trim(),
    active: true,
    mount_id: currentType.value === 'file' ? selectedMountId.value : undefined,
  })
  close()
}

function onValueInput() {
  if (currentType.value === 'file') {
    selectedMountId.value = undefined
  }
}

async function loadMountsAndFiles() {
  const projectId = projectStore.currentProjectId
  if (!projectId || currentType.value !== 'file') return
  await projectStore.fetchProjectMounts(projectId).catch(() => undefined)
  if (!activeMountId.value || !connectedLocalMounts.value.some((mount) => mount.id === activeMountId.value)) {
    activeMountId.value = connectedLocalMounts.value[0]?.id ?? ''
  }
  if (activeMountId.value) {
    await loadFiles('')
  }
}

async function loadFiles(path: string) {
  const projectId = projectStore.currentProjectId
  if (!projectId || !activeMountId.value) {
    entries.value = []
    return
  }
  loadingFiles.value = true
  fileError.value = ''
  try {
    const { data } = await projectsApi.listMountFiles(projectId, activeMountId.value, path)
    currentPath.value = data.path
    entries.value = data.entries
  } catch {
    entries.value = []
    fileError.value = '文件列表加载失败'
  } finally {
    loadingFiles.value = false
  }
}

function selectEntry(entry: MountFileEntry) {
  if (entry.kind === 'directory') {
    void loadFiles(entry.relative_path)
    return
  }
  value.value = entry.relative_path
  label.value = activeMount.value
    ? `${activeMount.value.display_name}/${entry.relative_path}`
    : entry.relative_path
  selectedMountId.value = activeMountId.value || undefined
}

function goParent() {
  if (!currentPath.value) return
  const parts = currentPath.value.split('/').filter(Boolean)
  parts.pop()
  void loadFiles(parts.join('/'))
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      currentType.value = 'file'
      value.value = ''
      label.value = ''
      selectedMountId.value = undefined
      currentPath.value = ''
      entries.value = []
      void loadMountsAndFiles()
    }
  },
)

watch(currentType, (type) => {
  if (type === 'file') {
    void loadMountsAndFiles()
  } else {
    selectedMountId.value = undefined
  }
})

watch(activeMountId, (mountId, previous) => {
  if (mountId && mountId !== previous && currentType.value === 'file') {
    selectedMountId.value = undefined
    value.value = ''
    label.value = ''
    void loadFiles('')
  }
})
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="context-picker-backdrop" @click="close">
      <div class="context-picker" @click.stop>
        <div class="context-picker__header">
          <span class="context-picker__title">{{ title }}</span>
          <button class="context-picker__icon-btn" title="关闭" @click="close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div class="context-picker__tabs">
          <button
            v-for="type in contextTypes"
            :key="type"
            class="context-picker__tab"
            :class="{ active: currentType === type }"
            @click="currentType = type"
          >
            {{ type === 'file' ? '文件' : type === 'branch' ? '分支' : '网址' }}
          </button>
        </div>

        <label class="context-picker__field">
          <span>值</span>
          <input v-model="value" :placeholder="placeholder" @input="onValueInput" @keydown.enter="submit" />
        </label>

        <div v-if="currentType === 'file'" class="context-picker__mounts">
          <div v-if="connectedLocalMounts.length > 0" class="mount-browser">
            <label class="context-picker__field">
              <span>代码库</span>
              <select v-model="activeMountId">
                <option v-for="mount in connectedLocalMounts" :key="mount.id" :value="mount.id">
                  {{ mount.display_name }}
                </option>
              </select>
            </label>

            <div class="file-browser">
              <div class="file-browser__bar">
                <button
                  class="file-browser__up"
                  :disabled="!currentPath"
                  title="返回上级"
                  @click="goParent"
                >
                  ↑
                </button>
                <span class="file-browser__path">{{ activeMount?.display_name }}{{ currentPath ? `/${currentPath}` : '' }}</span>
              </div>
              <div class="file-browser__list">
                <button
                  v-for="entry in entries"
                  :key="entry.relative_path"
                  class="file-browser__row"
                  :class="{ selected: selectedMountId === activeMountId && value === entry.relative_path }"
                  @click="selectEntry(entry)"
                >
                  <span class="file-browser__kind">{{ entry.kind === 'directory' ? '▸' : '·' }}</span>
                  <span class="file-browser__name">{{ entry.name }}</span>
                  <span v-if="entry.kind === 'file' && entry.size != null" class="file-browser__size">{{ entry.size }}B</span>
                </button>
                <span v-if="loadingFiles" class="file-browser__state">加载中...</span>
                <span v-else-if="fileError" class="file-browser__state">{{ fileError }}</span>
                <span v-else-if="entries.length === 0" class="file-browser__state">暂无可选文件</span>
              </div>
            </div>
          </div>
          <span v-else class="context-picker__empty">当前项目没有已连接的本地代码库</span>
        </div>

        <label class="context-picker__field">
          <span>显示名</span>
          <input v-model="label" placeholder="不填则使用值" @keydown.enter="submit" />
        </label>

        <div class="context-picker__footer">
          <button class="context-picker__secondary" @click="close">取消</button>
          <button class="context-picker__primary" :disabled="!canSubmit" @click="submit">添加</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped lang="scss">
.context-picker-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2400;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.24);
}

.context-picker {
  width: min(420px, 100%);
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.16);
}

.context-picker__header,
.context-picker__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.context-picker__title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.context-picker__icon-btn {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;

  &:hover { background: #f1f5f9; color: #0f172a; }
}

.context-picker__tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin: 16px 0;
}

.context-picker__tab {
  height: 30px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;

  &.active {
    border-color: #2563eb;
    background: #eff6ff;
    color: #1d4ed8;
    font-weight: 700;
  }
}

.context-picker__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;

  input,
  select {
    height: 36px;
    padding: 0 10px;
    border: 1px solid #dbe3ef;
    border-radius: 6px;
    font-size: 13px;
    color: #111827;
    outline: none;

    &:focus {
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
    }
  }
}

.context-picker__mounts {
  margin-bottom: 12px;
}

.context-picker__empty {
  display: block;
  padding: 10px;
  border: 1px dashed #dbe3ef;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.file-browser {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.file-browser__bar {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 8px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.file-browser__up {
  width: 24px;
  height: 24px;
  border: 1px solid #dbe3ef;
  border-radius: 6px;
  background: #fff;
  color: #475569;
  cursor: pointer;

  &:disabled {
    color: #cbd5e1;
    cursor: not-allowed;
  }
}

.file-browser__path {
  min-width: 0;
  overflow: hidden;
  color: #475569;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-browser__list {
  display: flex;
  flex-direction: column;
  max-height: 160px;
  overflow-y: auto;
}

.file-browser__row {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 8px;
  border: 0;
  background: #fff;
  color: #334155;
  font-size: 12px;
  text-align: left;
  cursor: pointer;

  &:hover {
    background: #f1f5f9;
  }

  &.selected {
    background: #eff6ff;
    color: #1d4ed8;
    font-weight: 700;
  }
}

.file-browser__kind,
.file-browser__size {
  color: #94a3b8;
}

.file-browser__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-browser__state {
  padding: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.context-picker__footer {
  justify-content: flex-end;
  margin-top: 16px;
}

.context-picker__secondary,
.context-picker__primary {
  height: 32px;
  padding: 0 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.context-picker__secondary {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
}

.context-picker__primary {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
  font-weight: 700;

  &:disabled {
    border-color: #cbd5e1;
    background: #e2e8f0;
    color: #94a3b8;
    cursor: not-allowed;
  }
}
</style>
