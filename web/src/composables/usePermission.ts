import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  function hasPermission(permission: string): boolean {
    return authStore.hasPermission(permission)
  }

  function isAdmin(): boolean {
    return authStore.isAdmin
  }

  const canManageAgents = computed(() => isAdmin())
  const canInstallSkills = computed(() => isAdmin())
  const canExportData = computed(() => isAdmin())

  return {
    hasPermission,
    isAdmin,
    canManageAgents,
    canInstallSkills,
    canExportData,
  }
}
