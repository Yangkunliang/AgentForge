import { defineStore } from 'pinia'
import { ref } from 'vue'
import { skillsApi } from '@/api/modules/skills'
import type { Skill, SkillInstall, InstallSkillForm } from '@/types'

export const useSkillStore = defineStore('skill', () => {
  const skills = ref<Skill[]>([])
  const installingTasks = ref<Map<string, SkillInstall>>(new Map())
  const loading = ref(false)

  async function fetchSkills() {
    loading.value = true
    try {
      const { data } = await skillsApi.list()
      skills.value = data.items
      return data
    } finally {
      loading.value = false
    }
  }

  async function installSkill(form: InstallSkillForm) {
    const { data } = await skillsApi.install(form)
    installingTasks.value.set(data.install_id, {
      install_id: data.install_id,
      skill_name: data.skill_name,
      status: 'pending',
    })
    return data
  }

  async function pollInstallStatus(installId: string) {
    const { data } = await skillsApi.getInstallStatus(installId)
    const task = installingTasks.value.get(installId)
    if (task) {
      task.status = data.status as SkillInstall['status']
      task.log = data.log
      task.error = data.error
    }
    return data
  }

  async function uninstallSkill(skillName: string) {
    await skillsApi.uninstall(skillName)
    skills.value = skills.value.filter((s) => s.name !== skillName)
  }

  function removeInstallTask(installId: string) {
    installingTasks.value.delete(installId)
  }

  return {
    skills,
    installingTasks,
    loading,
    fetchSkills,
    installSkill,
    pollInstallStatus,
    uninstallSkill,
    removeInstallTask,
  }
})
