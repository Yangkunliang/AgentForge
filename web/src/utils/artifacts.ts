import type { Artifact } from '@/types'

const ARTIFACT_TYPE_LABELS: Record<string, string> = {
  prd: 'PRD',
  architecture: '架构',
  api_spec: 'API',
  code: '代码',
  test: '测试',
  report: '报告',
  diff: 'Diff',
}

export function artifactTypeLabel(type: string): string {
  return ARTIFACT_TYPE_LABELS[type] ?? type
}

export function artifactStageLabel(artifact: Artifact): string {
  const stageName = artifact.metadata?.stage_name
  if (typeof stageName === 'string' && stageName.trim()) return stageName
  const stageId = artifact.metadata?.stage_id
  return typeof stageId === 'string' ? stageId : artifactTypeLabel(artifact.artifact_type)
}
