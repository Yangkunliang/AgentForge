import request from '@/api/request'
import type {
  CreateProjectForm,
  CreateProjectMountForm,
  CreateUploadMountForm,
  Artifact,
  BridgeStatus,
  CreateArtifactForm,
  GitHubOAuthStartForm,
  GitHubOAuthStartResponse,
  MountFileListResponse,
  MountFileReadResponse,
  Project,
  ProjectMount,
  Session,
} from '@/types'

export const projectsApi = {
  list: () => request.get<Project[]>('/projects'),

  create: (data: CreateProjectForm) => request.post<Project>('/projects', data),

  get: (projectId: string) => request.get<Project>(`/projects/${projectId}`),

  update: (projectId: string, data: Partial<CreateProjectForm> & { status?: string }) =>
    request.patch<Project>(`/projects/${projectId}`, data),

  delete: (projectId: string) => request.delete(`/projects/${projectId}`),

  listSessions: (projectId: string) =>
    request.get<Session[]>(`/projects/${projectId}/sessions`),

  createSession: (projectId: string, data: { title?: string; intent_type?: string | null } = {}) =>
    request.post<Session>(`/projects/${projectId}/sessions`, {
      title: data.title ?? '新对话',
      intent_type: data.intent_type ?? null,
    }),

  listMounts: (projectId: string) =>
    request.get<ProjectMount[]>(`/projects/${projectId}/mounts`),

  bridgeStatus: (projectId: string) =>
    request.get<BridgeStatus>(`/projects/${projectId}/bridge/status`),

  listMountFiles: (projectId: string, mountId: string, path = '') =>
    request.get<MountFileListResponse>(`/projects/${projectId}/mounts/${mountId}/files`, {
      params: { path },
    }),

  readMountFile: (projectId: string, mountId: string, path: string) =>
    request.post<MountFileReadResponse>(`/projects/${projectId}/mounts/${mountId}/files/read`, {
      path,
    }),

  createMount: (projectId: string, data: CreateProjectMountForm) =>
    request.post<ProjectMount>(`/projects/${projectId}/mounts`, {
      ...data,
      metadata: data.metadata ?? {},
    }),

  createUploadMount: (projectId: string, data: CreateUploadMountForm) => {
    const form = new FormData()
    form.append('display_name', data.display_name)
    form.append('role', data.role)
    data.files.forEach((file, index) => {
      form.append('files', file)
      const path = data.paths?.[index]?.trim() || file.name
      form.append('paths', path)
    })
    return request.post<ProjectMount>(`/projects/${projectId}/mounts/upload`, form)
  },

  startGitHubOAuthMount: (projectId: string, data: GitHubOAuthStartForm) =>
    request.post<GitHubOAuthStartResponse>(`/projects/${projectId}/mounts/github/oauth/start`, data),

  listArtifacts: (projectId: string) =>
    request.get<Artifact[]>(`/projects/${projectId}/artifacts`),

  createArtifact: (projectId: string, data: CreateArtifactForm) =>
    request.post<Artifact>(`/projects/${projectId}/artifacts`, {
      ...data,
      metadata: data.metadata ?? {},
    }),
}
