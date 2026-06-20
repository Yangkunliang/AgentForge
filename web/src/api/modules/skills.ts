import request from '../request'
import type { Skill, InstallSkillForm } from '@/types'

export const skillsApi = {
  list: () => {
    return request.get<{ total: number; items: Skill[] }>('/skills')
  },

  get: (skillName: string) => {
    return request.get<Skill>(`/skills/${skillName}`)
  },

  install: (data: InstallSkillForm) => {
    return request.post<{ install_id: string; skill_name: string; status: string }>(
      '/skills/install',
      data
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

  uninstall: (skillName: string) => {
    return request.delete(`/skills/${skillName}`)
  },
}
