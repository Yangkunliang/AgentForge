<script setup lang="ts">
import { RouterView } from 'vue-router'
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// 页面初始化时，若 token 已存在则拉取用户信息（处理刷新场景）
onMounted(() => {
  authStore.fetchMe()
})
</script>

<template>
  <RouterView />
</template>

<style>
#app {
  height: 100%;
}
</style>
