import request from '../request'
import type { Skill, InstallSkillForm, MarketplaceResponse } from '@/types'

export const skillsApi = {
  // ── 已安装 Skill ──────────────────────────────────────────

  list: (enabledOnly = false) => {
    return request.get<{ total: number; items: Skill[] }>('/skills', {
      params: { enabled_only: enabledOnly },
    })
  },

  get: (skillName: string) => {
    return request.get<Skill>(`/skills/${skillName}`)
  },

  // ── 安装 ──────────────────────────────────────────────────

  install: (data: InstallSkillForm) => {
    return request.post<{ install_id: string; skill_name: string; status: string }>(
      '/skills/install',
      data,
    )
  },

  installFromUrl: (data: InstallSkillForm) => {
    return request.post<{ install_id: string; skill_name: string; status: string }>(
      '/skills/install/url',
      data,
    )
  },

  getInstallStatus: (installId: string) => {
    return request.get<{
      install_id: string
      status: string
      log?: string
      error?: string
    }>(`/skills/install/${installId}`)
  },

  // ── 启用 / 禁用 ────────────────────────────────────────────

  enable: (skillName: string) => {
    return request.post<{ skill: string; enabled: boolean }>(`/skills/${skillName}/enable`)
  },

  disable: (skillName: string) => {
    return request.post<{ skill: string; enabled: boolean }>(`/skills/${skillName}/disable`)
  },

  // ── 卸载 ──────────────────────────────────────────────────

  uninstall: (skillName: string) => {
    return request.delete(`/skills/${skillName}`)
  },

  // ── 市场 ──────────────────────────────────────────────────

  marketplace: (params?: { source?: string; q?: string }) => {
    return request.get<MarketplaceResponse>('/skills/marketplace', { params })
  },
}
