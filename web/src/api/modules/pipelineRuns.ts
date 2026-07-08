import request from '@/api/request'
import type { ChatIntentType, PipelineRun, StageConfirmationAction } from '@/types'

export const pipelineRunsApi = {
  createForSession: (
    sessionId: string,
    data: { intent_type?: ChatIntentType | null; stage_overrides?: Record<string, boolean> } = {},
  ) =>
    request.post<PipelineRun>(`/sessions/${sessionId}/pipeline-runs`, {
      intent_type: data.intent_type ?? null,
      stage_overrides: data.stage_overrides ?? {},
    }),

  get: (runId: string) => request.get<PipelineRun>(`/pipeline-runs/${runId}`),

  skipStage: (runId: string, stageId: string) =>
    request.post<PipelineRun>(`/pipeline-runs/${runId}/stages/${stageId}/skip`, {}),

  restoreStage: (runId: string, stageId: string) =>
    request.post<PipelineRun>(`/pipeline-runs/${runId}/stages/${stageId}/restore`, {}),

  startStage: (runId: string, stageId: string) =>
    request.post<PipelineRun>(`/pipeline-runs/${runId}/stages/${stageId}/start`, {}),

  completeStage: (runId: string, stageId: string) =>
    request.post<PipelineRun>(`/pipeline-runs/${runId}/stages/${stageId}/complete`, {}),

  confirmStage: (
    runId: string,
    stageId: string,
    data: { action: StageConfirmationAction; feedback?: string | null },
  ) =>
    request.post<PipelineRun>(`/pipeline-runs/${runId}/stages/${stageId}/confirm`, {
      action: data.action,
      feedback: data.feedback ?? null,
    }),

  failStage: (runId: string, stageId: string) =>
    request.post<PipelineRun>(`/pipeline-runs/${runId}/stages/${stageId}/fail`, {}),
}
