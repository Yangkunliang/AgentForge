import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const globalLoading = ref(false)
  const globalError = ref<string | null>(null)

  // ── Mobile drawer state ──────────────────────────────────────
  const isMobile = ref(false)
  const sidebarOpen = ref(false)

  function checkMobile() {
    isMobile.value = window.innerWidth <= 768
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function openSidebar() {
    sidebarOpen.value = true
  }

  function closeSidebar() {
    sidebarOpen.value = false
  }

  // ── Global loading / error ───────────────────────────────────
  function setGlobalLoading(loading: boolean) {
    globalLoading.value = loading
  }

  function setGlobalError(error: string | null) {
    globalError.value = error
  }

  function clearGlobalError() {
    globalError.value = null
  }

  // ── Lifecycle ────────────────────────────────────────────────
  checkMobile()

  // Note: we intentionally do NOT add a window listener here —
  // the component that uses this store (AppHeader) is responsible
  // for listening to resize events.  This keeps the store tree-shakeable.

  return {
    sidebarCollapsed,
    globalLoading,
    globalError,
    isMobile,
    sidebarOpen,
    toggleSidebar,
    checkMobile,
    openSidebar,
    closeSidebar,
    setGlobalLoading,
    setGlobalError,
    clearGlobalError,
  }
})
