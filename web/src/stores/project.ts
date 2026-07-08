import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { projectsApi } from '@/api/modules/projects'
import type {
  CreateProjectForm,
  CreateProjectMountForm,
  Project,
  ProjectMount,
} from '@/types'

const CURRENT_PROJECT_KEY = 'agentforge.current_project_id'

function readStoredProjectId(): string | null {
  return localStorage.getItem(CURRENT_PROJECT_KEY)
}

function writeStoredProjectId(projectId: string | null) {
  if (projectId) {
    localStorage.setItem(CURRENT_PROJECT_KEY, projectId)
  } else {
    localStorage.removeItem(CURRENT_PROJECT_KEY)
  }
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProjectId = ref<string | null>(readStoredProjectId())
  const mountsByProject = ref<Record<string, ProjectMount[]>>({})
  const loading = ref(false)
  const mountLoading = ref(false)

  const currentProject = computed(() =>
    projects.value.find((project) => project.id === currentProjectId.value) ?? null
  )

  const hasProjects = computed(() => projects.value.length > 0)

  function setCurrentProject(projectId: string | null) {
    currentProjectId.value = projectId
    writeStoredProjectId(projectId)
  }

  function reconcileCurrentProject() {
    if (projects.value.length === 0) {
      setCurrentProject(null)
      return
    }

    const storedId = currentProjectId.value
    const exists = storedId && projects.value.some((project) => project.id === storedId)
    if (!exists) {
      setCurrentProject(projects.value[0].id)
    }
  }

  async function fetchProjects() {
    loading.value = true
    try {
      const { data } = await projectsApi.list()
      projects.value = data
      reconcileCurrentProject()
      return data
    } finally {
      loading.value = false
    }
  }

  async function selectProject(projectId: string) {
    if (!projects.value.some((project) => project.id === projectId)) {
      await fetchProjects()
    }
    const target = projects.value.find((project) => project.id === projectId) ?? null
    setCurrentProject(target?.id ?? null)
    return target
  }

  async function createProject(form: CreateProjectForm) {
    const { data } = await projectsApi.create({
      ...form,
      name: form.name.trim(),
      description: form.description?.trim() || null,
      tech_tags: [...new Set(form.tech_tags.map((tag) => tag.trim()).filter(Boolean))],
    })
    projects.value = [data, ...projects.value.filter((project) => project.id !== data.id)]
    setCurrentProject(data.id)
    return data
  }

  async function fetchProjectMounts(projectId: string) {
    mountLoading.value = true
    try {
      const { data } = await projectsApi.listMounts(projectId)
      mountsByProject.value = {
        ...mountsByProject.value,
        [projectId]: data,
      }
      return data
    } finally {
      mountLoading.value = false
    }
  }

  async function createMount(projectId: string, form: CreateProjectMountForm) {
    const { data } = await projectsApi.createMount(projectId, {
      ...form,
      locator: form.locator.trim(),
      display_name: form.display_name.trim(),
    })
    mountsByProject.value = {
      ...mountsByProject.value,
      [projectId]: [
        data,
        ...(mountsByProject.value[projectId] ?? []).filter((mount) => mount.id !== data.id),
      ],
    }
    return data
  }

  function primaryMountFor(projectId: string) {
    const mounts = mountsByProject.value[projectId] ?? []
    return mounts.find((mount) => mount.role === 'primary') ?? mounts[0] ?? null
  }

  return {
    projects,
    currentProjectId,
    currentProject,
    hasProjects,
    mountsByProject,
    loading,
    mountLoading,
    fetchProjects,
    selectProject,
    createProject,
    fetchProjectMounts,
    createMount,
    primaryMountFor,
  }
})
