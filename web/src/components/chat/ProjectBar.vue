<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { useSessionStore } from '@/stores/session'
import type { Project } from '@/types'

const router = useRouter()
const projectStore = useProjectStore()
const sessionStore = useSessionStore()

const dropdownVisible = ref(false)

const currentProject = computed(() => projectStore.currentProject)
const projects = computed(() => projectStore.projects)

onMounted(async () => {
  if (projects.value.length === 0) {
    await projectStore.fetchProjects()
  }
})

async function selectProject(project: Project) {
  await projectStore.selectProject(project.id)
  await sessionStore.fetchSessions(project.id)
  dropdownVisible.value = false
  if (router.currentRoute.value.path.startsWith('/chat/')) {
    router.push('/chat')
  }
}

function handleManageProjects() {
  dropdownVisible.value = false
  router.push('/projects')
}
</script>

<template>
  <div class="project-bar">
    <div class="project-info" @click="dropdownVisible = !dropdownVisible">
      <div class="project-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
      </div>
      <div class="project-detail">
        <span class="project-name">{{ currentProject?.name ?? '选择项目' }}</span>
        <span class="project-tech">
          {{ currentProject?.tech_tags?.length ? currentProject.tech_tags.join(' · ') : '暂无项目上下文' }}
        </span>
      </div>
      <svg class="arrow-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </div>

    <Transition name="dropdown">
      <div v-if="dropdownVisible" class="project-dropdown">
        <div class="dropdown-header">
          <span class="dropdown-title">切换项目</span>
          <button class="manage-btn" @click="handleManageProjects">管理项目</button>
        </div>
        <div class="dropdown-list">
          <div
            v-for="project in projects"
            :key="project.id"
            class="dropdown-item"
            :class="{ active: currentProject?.id === project.id }"
            @click="selectProject(project)"
          >
            <div class="item-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div class="item-info">
              <span class="item-name">{{ project.name }}</span>
              <span class="item-tech">{{ project.tech_tags.join(', ') || '未标注技术栈' }}</span>
            </div>
          </div>
          <div v-if="projects.length === 0" class="dropdown-empty">
            暂无项目，先创建一个项目
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped lang="scss">
.project-bar {
  position: relative;
}

.project-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #f3f4f6;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: #e5e7eb; }
}

.project-icon {
  color: #409eff;
}

.project-detail {
  display: flex;
  flex-direction: column;
}

.project-name {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
}

.project-tech {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
}

.arrow-icon {
  color: #9ca3af;
  flex-shrink: 0;
  transition: transform 0.15s;

  .project-info:hover & { transform: rotate(180deg); }
}

.project-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  left: auto;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  min-width: 240px;
  z-index: 200;
  overflow: hidden;
  border: 1px solid #f3f4f6;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #f3f4f6;
}

.dropdown-title {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.manage-btn {
  background: transparent;
  border: none;
  color: #409eff;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;

  &:hover { background: #f0f7ff; }
}

.dropdown-list {
  max-height: 200px;
  overflow-y: auto;
}

.dropdown-empty {
  padding: 14px;
  font-size: 12px;
  color: #9ca3af;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: #f9fafb; }

  &.active {
    background: #eff6ff;
    .item-icon { color: #409eff; }
    .item-name { color: #409eff; }
  }
}

.item-icon {
  color: #9ca3af;
}

.item-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.item-name {
  font-size: 13px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-tech {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
