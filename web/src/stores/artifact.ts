import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { artifactsApi } from '@/api/modules/artifacts'
import { projectsApi } from '@/api/modules/projects'
import type { Artifact } from '@/types'

export const useArtifactStore = defineStore('artifact', () => {
  const artifactsByProject = ref<Record<string, Artifact[]>>({})
  const currentArtifact = ref<Artifact | null>(null)
  const loading = ref(false)

  const allArtifacts = computed(() =>
    Object.values(artifactsByProject.value).flat()
  )

  function artifactsForProject(projectId: string): Artifact[] {
    return artifactsByProject.value[projectId] ?? []
  }

  function upsertArtifact(artifact: Artifact) {
    const existingProjectArtifacts = artifactsByProject.value[artifact.project_id] ?? []
    artifactsByProject.value = {
      ...artifactsByProject.value,
      [artifact.project_id]: [
        artifact,
        ...existingProjectArtifacts.filter((item) => item.id !== artifact.id),
      ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    }

    if (currentArtifact.value?.id === artifact.id) {
      currentArtifact.value = artifact
    }
  }

  async function fetchProjectArtifacts(projectId: string) {
    loading.value = true
    try {
      const { data } = await projectsApi.listArtifacts(projectId)
      artifactsByProject.value = {
        ...artifactsByProject.value,
        [projectId]: data,
      }
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchArtifact(artifactId: string) {
    loading.value = true
    try {
      const { data } = await artifactsApi.get(artifactId)
      currentArtifact.value = data
      upsertArtifact(data)
      return data
    } finally {
      loading.value = false
    }
  }

  return {
    artifactsByProject,
    currentArtifact,
    loading,
    allArtifacts,
    artifactsForProject,
    fetchProjectArtifacts,
    fetchArtifact,
    upsertArtifact,
  }
})
