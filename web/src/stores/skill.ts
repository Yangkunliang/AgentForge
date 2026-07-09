import { defineStore } from 'pinia'
import { ref } from 'vue'
import { skillsApi } from '@/api/modules/skills'
import type { Skill, SkillInstall, InstallSkillForm, MarketplaceSkill } from '@/types'

export const useSkillStore = defineStore('skill', () => {
  // ── 已安装 Skill ──────────────────────────────────────────
  const skills = ref<Skill[]>([])
  const loading = ref(false)

  // ── 安装进度 ──────────────────────────────────────────────
  const installingTasks = ref<Map<string, SkillInstall>>(new Map())

  // ── 市场 ──────────────────────────────────────────────────
  const marketplaceItems = ref<MarketplaceSkill[]>([])
  const marketplaceLoading = ref(false)
  const marketplaceTotal = ref(0)

  // ── 已安装 Skill 操作 ─────────────────────────────────────

  async function fetchSkills(enabledOnly = false) {
    loading.value = true
    try {
      const { data } = await skillsApi.list(enabledOnly)
      skills.value = data.items
      return data
    } finally {
      loading.value = false
    }
  }

  async function enableSkill(skillName: string) {
    await skillsApi.enable(skillName)
    const skill = skills.value.find((s) => s.name === skillName)
    if (skill) skill.enabled = true
  }

  async function disableSkill(skillName: string) {
    await skillsApi.disable(skillName)
    const skill = skills.value.find((s) => s.name === skillName)
    if (skill) skill.enabled = false
  }

  async function uninstallSkill(skillName: string) {
    await skillsApi.uninstall(skillName)
    skills.value = skills.value.filter((s) => s.name !== skillName)
  }

  // ── 安装 Skill ────────────────────────────────────────────

  async function installSkill(form: InstallSkillForm) {
    const { data } = await skillsApi.install(form)
    installingTasks.value.set(data.install_id, {
      install_id: data.install_id,
      skill_name: data.skill_name,
      status: 'pending',
    })
    return data
  }

  async function previewSkillImport(form: InstallSkillForm) {
    const { data } = await skillsApi.previewImport(form)
    return data
  }

  async function installSkillImport(form: InstallSkillForm) {
    const { data } = await skillsApi.installImport(form)
    installingTasks.value.set(data.install_id, {
      install_id: data.install_id,
      skill_name: data.skill_name,
      status: data.status as SkillInstall['status'],
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

  function removeInstallTask(installId: string) {
    installingTasks.value.delete(installId)
  }

  // ── Skill 市场 ────────────────────────────────────────────

  async function fetchMarketplace(params?: { source?: string; q?: string }) {
    marketplaceLoading.value = true
    try {
      const { data } = await skillsApi.marketplace(params)
      marketplaceItems.value = data.items
      marketplaceTotal.value = data.total
      return data
    } finally {
      marketplaceLoading.value = false
    }
  }

  async function installFromMarketplace(item: MarketplaceSkill) {
    const form: InstallSkillForm = {
      source: item.url || item.name,
      version: item.version === 'latest' ? undefined : item.version,
    }
    return installSkill(form)
  }

  return {
    // installed
    skills,
    loading,
    fetchSkills,
    enableSkill,
    disableSkill,
    uninstallSkill,
    // install tasks
    installingTasks,
    installSkill,
    previewSkillImport,
    installSkillImport,
    pollInstallStatus,
    removeInstallTask,
    // marketplace
    marketplaceItems,
    marketplaceLoading,
    marketplaceTotal,
    fetchMarketplace,
    installFromMarketplace,
  }
})
