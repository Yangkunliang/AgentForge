<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './AppSidebar.vue'

const route = useRoute()
const isFullHeight = computed(() => route.meta.fullHeight === true)
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <main class="app-content" :class="{ 'app-content--full': isFullHeight }">
      <router-view />
    </main>
  </div>
</template>

<style scoped lang="scss">
.app-layout {
  height: 100vh;
  display: flex;
  overflow: hidden;
}

.app-content {
  flex: 1;
  padding: $spacing-lg;
  overflow-y: auto;
  background: #f5f7fa;
  min-width: 0;

  &--full {
    padding: 0;
    overflow: hidden;
    background: #fff;
  }
}
</style>
