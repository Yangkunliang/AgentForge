<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { usePermission } from '@/composables'

const route = useRoute()
const { isAdmin } = usePermission()

interface MenuItem {
  path: string
  label: string
  icon: string
  adminOnly?: boolean
}

const menuItems: MenuItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: 'Odometer' },
  { path: '/tasks', label: '任务', icon: 'List' },
  { path: '/agents', label: 'Agent', icon: 'User', adminOnly: true },
  { path: '/skills', label: 'Skill', icon: 'Grid' },
  { path: '/exports', label: '导出', icon: 'Download', adminOnly: true },
]

const visibleMenuItems = computed(() => {
  return menuItems.filter((item) => !item.adminOnly || isAdmin.value)
})

const activeMenu = computed(() => route.path)
</script>

<template>
  <el-aside class="app-sidebar" width="220px">
    <el-menu :default-active="activeMenu" :router="true" class="sidebar-menu">
      <el-menu-item
        v-for="item in visibleMenuItems"
        :key="item.path"
        :index="item.path"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </el-menu-item>
    </el-menu>
  </el-aside>
</template>

<style scoped lang="scss">
.app-sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.sidebar-menu {
  border-right: none;
}
</style>
