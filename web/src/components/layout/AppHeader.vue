<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const authStore = useAuthStore()
const appStore = useAppStore()

const username = computed(() => authStore.user?.username ?? 'User')

function toggleMobileSidebar() {
  if (appStore.sidebarOpen) {
    appStore.closeSidebar()
  } else {
    appStore.openSidebar()
  }
}

function handleResize() {
  appStore.checkMobile()
}

onMounted(() => {
  window.addEventListener('resize', handleResize, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

async function handleLogout() {
  await authStore.logout()
}
</script>

<template>
  <el-header class="app-header">
    <div class="header-left">
      <!-- Hamburger button (mobile only) -->
      <button
        class="hamburger-btn"
        :class="{ 'hamburger-btn--open': appStore.sidebarOpen }"
        @click="toggleMobileSidebar"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <h1 class="logo">AgentForge</h1>
    </div>
    <div class="header-right">
      <el-dropdown @command="handleLogout">
        <span class="user-info">
          <el-icon><User /></el-icon>
          <span>{{ username }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: $header-height;
  padding: 0 $spacing-lg;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.logo {
  font-size: 20px;
  font-weight: 600;
  color: #409eff;
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  cursor: pointer;
  color: #606266;
}

// ── Hamburger button (mobile only) ────────────────────────────
.hamburger-btn {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: #606266;
  border-radius: 4px;
  transition: background 0.15s;

  &:hover {
    background: #f3f4f6;
  }

  &--open {
    color: #409eff;
  }
}

@media (max-width: $breakpoint-mobile) {
  .app-header {
    padding: 0 $spacing-md;
  }

  .hamburger-btn {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .logo {
    font-size: 18px;
  }
}
</style>
