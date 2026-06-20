<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username ?? 'User')

async function handleLogout() {
  await authStore.logout()
}
</script>

<template>
  <el-header class="app-header">
    <div class="header-left">
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
</style>
