import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  function hasPermission(permission: string): boolean {
    return authStore.hasPermission(permission)
  }

  const isAdmin = computed(() => authStore.isAdmin)

  const canManageAgents = computed(() => authStore.isAdmin)
  const canInstallSkills = computed(() => authStore.isAdmin)
  const canExportData = computed(() => authStore.isAdmin)

  return {
    hasPermission,
    isAdmin,
    canManageAgents,
    canInstallSkills,
    canExportData,
  }
}
