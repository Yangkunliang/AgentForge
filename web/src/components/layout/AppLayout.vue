<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'

const route = useRoute()
const isFullHeight = computed(() => route.meta.fullHeight === true)
</script>

<template>
  <div class="app-layout">
    <AppHeader />
    <div class="app-main">
      <AppSidebar />
      <main class="app-content" :class="{ 'app-content--full': isFullHeight }">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.app-content {
  flex: 1;
  padding: $spacing-lg;
  overflow-y: auto;
  background: #f5f7fa;

  &--full {
    padding: 0;
    overflow: hidden;
    background: #fff;
  }
}
</style>
