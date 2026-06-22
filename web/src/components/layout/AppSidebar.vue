<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { usePermission } from '@/composables'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()
const { isAdmin } = usePermission()

interface MenuItem {
  path: string
  label: string
  title: string
  icon: string
  adminOnly?: boolean
}

const menuItems: MenuItem[] = [
  { path: '/chat',         label: '会话',     title: 'AI 对话',           icon: 'chat' },
  { path: '/dashboard',   label: 'Dashboard', title: '数据看板',           icon: 'dashboard' },
  { path: '/tasks',       label: '任务',      title: '任务管理',           icon: 'tasks' },
  { path: '/agents',      label: 'Agent',     title: 'Agent 管理',         icon: 'agents', adminOnly: true },
  { path: '/skills',      label: 'Skill',     title: '技能市场',           icon: 'skills' },
  { path: '/exports',     label: '导出',      title: '数据导出',           icon: 'exports', adminOnly: true },
  { path: '/settings/llm', label: 'LLM 配置', title: 'LLM 模型配置',       icon: 'settings' },
]

const iconMap: Record<string, string> = {
  chat:     'M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z',
  dashboard:'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
  tasks:    'M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11',
  agents:   'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  skills:   'M12 2l4.5 4.5L12 11l-4.5-4.5L12 2zm0 12l4.5 4.5L12 23l-4.5-4.5L12 14z',
  exports:  'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z',
}

const visibleMenuItems = computed(() =>
  menuItems.filter((item) => !item.adminOnly || isAdmin.value)
)

const activePath = computed(() => route.path)

function isActive(itemPath: string): boolean {
  if (itemPath === '/chat') {
    return activePath.value === '/chat' || activePath.value.startsWith('/chat/')
  }
  return activePath.value === itemPath || activePath.value.startsWith(itemPath + '/')
}

function navigate(path: string) {
  router.push(path)
}

async function handleLogout() {
  await authStore.logout()
}

// Mobile drawer — keep existing mobile support via appStore
const drawerVisible = computed({
  get: () => appStore.sidebarOpen,
  set: (val: boolean) => { if (!val) appStore.closeSidebar() },
})

watch(() => route.path, () => {
  if (appStore.sidebarOpen) appStore.closeSidebar()
})
</script>

<template>
  <!-- Desktop: narrow icon nav column -->
  <nav class="app-nav" aria-label="主导航">
    <!-- CodeSoul logo -->
    <div class="nav-logo" title="CodeSoul">
      <div class="logo-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
          <path d="M7 8l-2 2 2 2M17 8l2 2-2 2M13 7l-2 6"/>
        </svg>
      </div>
      <span class="logo-label">CodeSoul</span>
    </div>

    <!-- Nav items -->
    <div class="nav-items">
      <button
          v-for="item in visibleMenuItems"
          :key="item.path"
          class="nav-item"
          :class="{ 'nav-item--active': isActive(item.path) }"
          :title="item.title"
          @click="navigate(item.path)"
        >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path :d="iconMap[item.icon]" />
        </svg>
      </button>
    </div>

    <!-- Bottom: logout -->
    <div class="nav-bottom">
      <button class="nav-item nav-item--logout" title="退出登录" @click="handleLogout">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
        </svg>
      </button>
    </div>
  </nav>

  <!-- Mobile drawer -->
  <el-drawer
    v-model="drawerVisible"
    :with-header="false"
    direction="ltr"
    size="220px"
    class="nav-drawer"
  >
    <div class="drawer-inner">
      <div class="drawer-logo">CodeSoul</div>
      <button
        v-for="item in visibleMenuItems"
        :key="item.path"
        class="drawer-item"
        :class="{ 'drawer-item--active': isActive(item.path) }"
        @click="navigate(item.path)"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path :d="iconMap[item.icon]" />
        </svg>
        {{ item.label }}
      </button>
      <button class="drawer-item drawer-item--logout" @click="handleLogout">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
        </svg>
        退出登录
      </button>
    </div>
  </el-drawer>
</template>

<style scoped lang="scss">
// ── Desktop nav column ───────────────────────────────────────
.app-nav {
  width: 56px;
  height: 100vh;
  background: #f9f9f9;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  flex-shrink: 0;
  z-index: 10;
}

.nav-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-bottom: 16px;
  cursor: default;
}

.logo-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-label {
  font-size: 8px;
  font-weight: 600;
  color: #409eff;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.nav-items {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 0 8px;
}

.nav-item {
  width: 40px;
  height: 40px;
  border-radius: $border-radius-md;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #9ca3af;
  transition: background 0.15s, color 0.15s;

  &:hover {
    background: #f0f0f0;
    color: #374151;
  }

  &--active {
    background: #eff6ff;
    color: #409eff;
  }

  &--logout {
    color: #9ca3af;
    &:hover { color: #ef4444; background: #fef2f2; }
  }
}

.nav-bottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 8px;
  width: 100%;
}

// Mobile: hide desktop nav
@media (max-width: $breakpoint-mobile) {
  .app-nav {
    display: none;
  }
}

// ── Mobile drawer ────────────────────────────────────────────
.nav-drawer {
  :deep(.el-drawer__body) {
    padding: 0;
    background: #fff;
  }
}

.drawer-inner {
  display: flex;
  flex-direction: column;
  padding: 16px 0 12px;
  height: 100%;
}

.drawer-logo {
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
  padding: 0 16px 16px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 8px;
}

.drawer-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
  text-align: left;
  transition: background 0.15s;

  &:hover { background: #f3f4f6; }

  &--active {
    color: #409eff;
    background: #eff6ff;
    font-weight: 500;
  }

  &--logout {
    margin-top: auto;
    color: #9ca3af;
    &:hover { color: #ef4444; background: #fef2f2; }
  }
}
</style>
