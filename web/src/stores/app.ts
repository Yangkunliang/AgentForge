import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const globalLoading = ref(false)
  const globalError = ref<string | null>(null)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setGlobalLoading(loading: boolean) {
    globalLoading.value = loading
  }

  function setGlobalError(error: string | null) {
    globalError.value = error
  }

  function clearGlobalError() {
    globalError.value = null
  }

  return {
    sidebarCollapsed,
    globalLoading,
    globalError,
    toggleSidebar,
    setGlobalLoading,
    setGlobalError,
    clearGlobalError,
  }
})
